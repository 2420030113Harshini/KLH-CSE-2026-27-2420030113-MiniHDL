"""
testgen.py -- Manufacturing-test analysis: stuck-at faults and ATPG.

After a chip is fabricated, a defect typically shows up as a net permanently
stuck at 0 or 1.  This module answers two questions about a netlist:

  * Fault coverage:   what fraction of all single stuck-at faults can ANY
                      input vector expose at the outputs?
  * Test generation:  what is a small set of vectors that exposes all of the
                      detectable ones?

Technique: *bit-parallel fault simulation*.  Every net holds one Python int
whose bit v is that net's value under input vector v, so a single AND/OR/XOR
evaluates every vector at once.  A fault is detected by the vectors where the
faulty outputs differ from the fault-free outputs.

Faults that no vector can detect are *redundant*: they mark logic that has no
effect on any output.  An unoptimized netlist usually has some; a well
optimized one should have none, which makes coverage a second, independent
quality metric for the optimizer.
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple

from .ir import Netlist, ZERO, ONE

EXHAUSTIVE_BITS = 12
RANDOM_VECTORS = 4096


def _gate(op: str, v: List[int], M: int) -> int:
    if op == "BUF":  return v[0]
    if op == "NOT":  return ~v[0] & M
    if op == "AND":  return v[0] & v[1]
    if op == "OR":   return v[0] | v[1]
    if op == "XOR":  return v[0] ^ v[1]
    if op == "NAND": return ~(v[0] & v[1]) & M
    if op == "NOR":  return ~(v[0] | v[1]) & M
    if op == "XNOR": return ~(v[0] ^ v[1]) & M
    if op == "MUX":  return (v[0] & v[1]) | (~v[0] & v[2] & M)
    raise ValueError(op)


def _patterns(nl: Netlist) -> Tuple[Dict[int, int], int, int, bool]:
    nets = nl.input_nets()
    exhaustive = len(nets) <= EXHAUSTIVE_BITS
    N = (1 << len(nets)) if exhaustive else RANDOM_VECTORS
    M = (1 << N) - 1
    pat: Dict[int, int] = {}
    rng = random.Random(7)
    for k, n in enumerate(nets):
        if exhaustive:
            p = 0
            for v in range(N):
                if (v >> k) & 1:
                    p |= 1 << v
            pat[n] = p
        else:
            pat[n] = rng.getrandbits(N)
    return pat, N, M, exhaustive


def _evaluate(nl: Netlist, pat: Dict[int, int], M: int,
              fault: Optional[Tuple[int, int]] = None) -> List[int]:
    val = {ZERO: 0, ONE: M}
    val.update(pat)
    if fault and fault[0] in val and fault[0] not in (ZERO, ONE):
        val[fault[0]] = M if fault[1] else 0
    for g in nl.gates:
        out = _gate(g.op, [val.get(i, 0) for i in g.ins], M)
        if fault and g.out == fault[0]:
            out = M if fault[1] else 0
        val[g.out] = out
    return [val.get(n, 0) for n in nl.output_nets()]


def analyze(nl: Netlist) -> dict:
    pat, N, M, exhaustive = _patterns(nl)
    good = _evaluate(nl, pat, M)
    sites = list(dict.fromkeys(nl.input_nets() + [g.out for g in nl.gates]))
    sites = [s for s in sites if s not in (ZERO, ONE)]

    detect: Dict[Tuple[int, int], int] = {}
    for s in sites:
        for sv in (0, 1):
            bad = _evaluate(nl, pat, M, (s, sv))
            diff = 0
            for a, b in zip(good, bad):
                diff |= a ^ b
            detect[(s, sv)] = diff

    detected = {f for f, d in detect.items() if d}
    redundant = sorted(f for f, d in detect.items() if not d)

    # Greedy test selection: take an undetected fault, pick (among a few of
    # its detecting vectors) the one that also catches the most other faults.
    tests: List[int] = []
    left = set(detected)
    while left:
        f = min(left)
        d, cands = detect[f], []
        while d and len(cands) < 64:
            low = d & -d
            cands.append(low.bit_length() - 1)
            d ^= low
        best = max(cands, key=lambda v: sum((detect[g] >> v) & 1 for g in left))
        tests.append(best)
        left = {g for g in left if not (detect[g] >> best) & 1}

    in_vars = [(name, len(n)) for name, n in nl.inputs]
    vectors = []
    for v in tests:
        assign, k = {}, 0
        for name, w in in_vars:
            x = 0
            for i in range(w):
                x |= ((pat[nl.input_nets()[k]] >> v) & 1) << i
                k += 1
            assign[name] = x
        expect, j = {}, 0
        for name, nets in nl.outputs:
            x = 0
            for i in range(len(nets)):
                x |= ((good[j] >> v) & 1) << i
                j += 1
            expect[name] = x
        vectors.append((assign, expect))

    total = len(detect)
    return {"total": total, "detected": len(detected),
            "coverage": round(100.0 * len(detected) / total, 1) if total else 100.0,
            "redundant": [(nl.net_label(n), sv) for n, sv in redundant],
            "tests": vectors, "exhaustive": exhaustive, "space": N}


def report(nl: Netlist) -> str:
    r = analyze(nl)
    L = [f"  fault sites        : {r['total'] // 2} nets x 2 polarities = {r['total']} faults",
         f"  detected           : {r['detected']}  ({r['coverage']}% coverage)",
         f"  search space       : {r['space']} vectors "
         f"({'exhaustive' if r['exhaustive'] else 'random sample'})"]
    if r["redundant"]:
        L.append("  undetectable (redundant logic): " +
                 ", ".join(f"{n} stuck-at-{sv}" for n, sv in r["redundant"][:12]) +
                 (" ..." if len(r["redundant"]) > 12 else ""))
    else:
        L.append("  undetectable       : none  (every fault is observable)")
    L.append(f"  generated tests    : {len(r['tests'])} vector(s) cover all detectable faults")
    L.append("")
    for k, (a, e) in enumerate(r["tests"][:16], 1):
        ins = " ".join(f"{n}={v}" for n, v in a.items())
        outs = " ".join(f"{n}={v}" for n, v in e.items())
        L.append(f"    t{k:<2} {ins:<28} -> expect {outs}")
    if len(r["tests"]) > 16:
        L.append(f"    ... and {len(r['tests']) - 16} more")
    return "\n".join(L)
