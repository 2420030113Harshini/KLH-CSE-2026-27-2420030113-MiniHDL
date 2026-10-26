"""
simulator.py -- Verification support.

Three services built on one evaluator:

*   `simulate`        -- evaluate a netlist for one input vector.
*   `truth_table`     -- exhaustively enumerate a small design.
*   `check_equivalence` -- prove (exhaustively for <= 16 input bits, otherwise
    by random sampling) that the optimizer preserved the circuit's behaviour.

The last one is the reason this file exists: an optimizing compiler you cannot
validate is an optimizing compiler you should not trust.  `--verify` runs the
unoptimized and optimized netlists side by side and reports the first vector on
which they disagree.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple

from .ir import Netlist, ZERO, ONE
from .diagnostics import Color


def _eval_gate(op: str, v: List[int]) -> int:
    if op == "BUF":
        return v[0]
    if op == "NOT":
        return 1 - v[0]
    if op == "AND":
        return v[0] & v[1]
    if op == "OR":
        return v[0] | v[1]
    if op == "XOR":
        return v[0] ^ v[1]
    if op == "NAND":
        return 1 - (v[0] & v[1])
    if op == "NOR":
        return 1 - (v[0] | v[1])
    if op == "XNOR":
        return 1 - (v[0] ^ v[1])
    if op == "MUX":
        return v[1] if v[0] else v[2]
    raise ValueError(f"unknown gate op {op!r}")


def simulate(nl: Netlist, inputs: Dict[str, int]) -> Dict[str, int]:
    """Evaluate the netlist.  `inputs` maps a port name to an integer value."""
    val: Dict[int, int] = {ZERO: 0, ONE: 1}
    for name, nets in nl.inputs:
        iv = inputs.get(name, 0)
        for i, n in enumerate(nets):
            val[n] = (iv >> i) & 1

    drivers = {g.out: g for g in nl.gates}

    # Iterative DFS keeps evaluation correct even if a pass ever reorders gates.
    def value_of(net: int) -> int:
        if net in val:
            return val[net]
        stack = [(net, False)]
        while stack:
            n, expanded = stack.pop()
            if n in val:
                continue
            g = drivers.get(n)
            if g is None:
                val[n] = 0
                continue
            if expanded:
                val[n] = _eval_gate(g.op, [val.get(i, 0) for i in g.ins])
            else:
                stack.append((n, True))
                for i in g.ins:
                    if i not in val:
                        stack.append((i, False))
        return val[net]

    for g in nl.gates:                      # fast linear pass (topological)
        if g.out not in val:
            if all(i in val for i in g.ins):
                val[g.out] = _eval_gate(g.op, [val[i] for i in g.ins])

    out: Dict[str, int] = {}
    for name, nets in nl.outputs:
        acc = 0
        for i, n in enumerate(nets):
            acc |= value_of(n) << i
        out[name] = acc
    return out


def input_bit_count(nl: Netlist) -> int:
    return sum(len(nets) for _, nets in nl.inputs)


def _vectors(nl: Netlist):
    """Yield every input assignment as a dict, LSB-first bit packing."""
    widths = [(name, len(nets)) for name, nets in nl.inputs]
    total = sum(w for _, w in widths)
    for bits in range(1 << total):
        assign, shift = {}, 0
        for name, w in widths:
            assign[name] = (bits >> shift) & ((1 << w) - 1)
            shift += w
        yield assign


def truth_table(nl: Netlist, limit_bits: int = 12) -> str:
    total = input_bit_count(nl)
    if total == 0:
        return "  (module has no inputs)"
    if total > limit_bits:
        return (f"  truth table suppressed: {total} input bits would need "
                f"{1 << total} rows (limit {limit_bits})")
    in_names = [n for n, _ in nl.inputs]
    out_names = [n for n, _ in nl.outputs]
    widths = {n: len(v) for n, v in nl.inputs}
    owidths = {n: len(v) for n, v in nl.outputs}

    colw = {n: max(len(n), widths[n]) for n in in_names}
    ocolw = {n: max(len(n), owidths[n]) for n in out_names}

    head = " | ".join(n.rjust(colw[n]) for n in in_names) + " || " + \
           " | ".join(n.rjust(ocolw[n]) for n in out_names)
    rows = [Color.paint(head, Color.BOLD), "-" * len(head)]
    for assign in _vectors(nl):
        res = simulate(nl, assign)
        left = " | ".join(format(assign[n], "0%db" % widths[n]).rjust(colw[n])
                          for n in in_names)
        right = " | ".join(format(res[n], "0%db" % owidths[n]).rjust(ocolw[n])
                           for n in out_names)
        rows.append(f"{left} || {right}")
    return "\n".join("  " + r for r in rows)


def check_equivalence(a: Netlist, b: Netlist, max_exhaustive: int = 16,
                      samples: int = 4096) -> Tuple[bool, Optional[dict], int]:
    """Compare two netlists.  Returns (ok, counterexample, vectors_tested)."""
    total = input_bit_count(a)
    names_a = [n for n, _ in a.inputs]
    widths = {n: len(v) for n, v in a.inputs}

    def compare(assign) -> Optional[dict]:
        ra, rb = simulate(a, assign), simulate(b, assign)
        if ra != rb:
            return {"inputs": assign, "reference": ra, "optimized": rb}
        return None

    tested = 0
    if total <= max_exhaustive:
        for assign in _vectors(a):
            tested += 1
            bad = compare(assign)
            if bad:
                return False, bad, tested
        return True, None, tested

    rng = random.Random(0xC0FFEE)
    for _ in range(samples):
        tested += 1
        assign = {n: rng.getrandbits(widths[n]) for n in names_a}
        bad = compare(assign)
        if bad:
            return False, bad, tested
    return True, None, tested
