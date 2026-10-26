"""
ir.py -- Intermediate Representation.

MiniHDL lowers to a *gate-level netlist*, which is the hardware analogue of
three-address code:

        t3 = AND t1, t2          <=>      Gate(op='AND', ins=[1,2], out=3)

Design notes
------------
*   Nets are small integers.  Net 0 is the constant ZERO and net 1 is the
    constant ONE; reserving them makes constant folding trivial.
*   The netlist is kept in *topological order* by construction: a gate is only
    ever appended after the gates producing its inputs.  Every pass preserves
    this invariant, so simulation is a single linear sweep.
*   `MUX(s, a, b)` evaluates to `a` when `s` is 1, else `b`.  It is the merge
    node produced by `when` statements -- effectively an SSA phi-function.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

ZERO = 0
ONE = 1

# op -> (arity, area in gate-equivalents, unit delay)
GATE_INFO: Dict[str, Tuple[int, float, int]] = {
    "BUF":  (1, 0.5, 1),
    "NOT":  (1, 1.0, 1),
    "AND":  (2, 2.0, 1),
    "OR":   (2, 2.0, 1),
    "XOR":  (2, 3.0, 2),
    "NAND": (2, 1.5, 1),
    "NOR":  (2, 1.5, 1),
    "XNOR": (2, 3.0, 2),
    "MUX":  (3, 3.5, 2),
}

COMMUTATIVE = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR"}


@dataclass
class Gate:
    op: str
    ins: List[int]
    out: int
    label: str = ""          # provenance, e.g. the source line that made it

    def key(self):
        """Canonical key used by common-subexpression elimination."""
        ins = tuple(sorted(self.ins)) if self.op in COMMUTATIVE else tuple(self.ins)
        return (self.op, ins)

    def __str__(self):
        return f"n{self.out} = {self.op} " + ", ".join(f"n{i}" for i in self.ins)


class Netlist:
    def __init__(self, name: str):
        self.name = name
        self.net_count = 2                       # nets 0 and 1 are the constants
        self.net_name: Dict[int, str] = {ZERO: "1'b0", ONE: "1'b1"}
        self.gates: List[Gate] = []
        self.inputs: List[Tuple[str, List[int]]] = []
        self.outputs: List[Tuple[str, List[int]]] = []

    # ------------------------------------------------------------ building
    def new_net(self, name: str = "") -> int:
        n = self.net_count
        self.net_count += 1
        if name:
            self.net_name[n] = name
        return n

    def emit(self, op: str, ins: List[int], label: str = "") -> int:
        out = self.new_net()
        self.gates.append(Gate(op, list(ins), out, label))
        return out

    def add_input(self, name: str, nets: List[int]):
        self.inputs.append((name, list(nets)))

    def add_output(self, name: str, nets: List[int]):
        self.outputs.append((name, list(nets)))

    # ------------------------------------------------------------- queries
    def drivers(self) -> Dict[int, Gate]:
        return {g.out: g for g in self.gates}

    def input_nets(self) -> List[int]:
        return [n for _, nets in self.inputs for n in nets]

    def output_nets(self) -> List[int]:
        return [n for _, nets in self.outputs for n in nets]

    def fanout(self) -> Dict[int, int]:
        f: Dict[int, int] = {}
        for g in self.gates:
            for i in g.ins:
                f[i] = f.get(i, 0) + 1
        for n in self.output_nets():
            f[n] = f.get(n, 0) + 1
        return f

    def net_label(self, n: int) -> str:
        return self.net_name.get(n, f"n{n}")

    # --------------------------------------------------------------- stats
    def stats(self) -> dict:
        by_op: Dict[str, int] = {}
        area = 0.0
        for g in self.gates:
            by_op[g.op] = by_op.get(g.op, 0) + 1
            area += GATE_INFO.get(g.op, (0, 1.0, 1))[1]
        return {
            "gates": len(self.gates),
            "by_op": dict(sorted(by_op.items())),
            "nets": self.net_count,
            "inputs": sum(len(v) for _, v in self.inputs),
            "outputs": sum(len(v) for _, v in self.outputs),
            "area_ge": round(area, 1),
            "depth": self.critical_path(),
        }

    def critical_path(self) -> int:
        """Longest input-to-output delay in unit gate delays."""
        depth: Dict[int, int] = {ZERO: 0, ONE: 0}
        for n in self.input_nets():
            depth[n] = 0
        for g in self.gates:
            d = GATE_INFO.get(g.op, (0, 1.0, 1))[2]
            depth[g.out] = max((depth.get(i, 0) for i in g.ins), default=0) + d
        outs = self.output_nets()
        return max((depth.get(n, 0) for n in outs), default=0)

    # ------------------------------------------------------------- display
    def dump(self) -> str:
        lines = [f"; netlist for module '{self.name}'"]
        for name, nets in self.inputs:
            lines.append(f"input  {name:<10} = [{', '.join('n%d' % n for n in nets)}]")
        for name, nets in self.outputs:
            lines.append(f"output {name:<10} = [{', '.join('n%d' % n for n in nets)}]")
        lines.append(";" + "-" * 50)
        for g in self.gates:
            note = f"   ; {g.label}" if g.label else ""
            lines.append("  " + str(g) + note)
        return "\n".join(lines)

    def to_dot(self) -> str:
        """Graphviz rendering of the circuit (render with: dot -Tsvg x.dot)."""
        L = ["digraph " + _ident(self.name) + " {",
             "  rankdir=LR;",
             '  node [fontname="Helvetica", fontsize=10];',
             '  edge [fontname="Helvetica", fontsize=8, color="#555555"];']
        L.append("  { rank=source;")
        for name, nets in self.inputs:
            for k, n in enumerate(nets):
                lbl = name if len(nets) == 1 else f"{name}[{k}]"
                L.append(f'    n{n} [label="{lbl}", shape=invhouse, '
                         f'style=filled, fillcolor="#cde7c8"];')
        L.append("  }")
        used_consts = {i for g in self.gates for i in g.ins if i in (ZERO, ONE)}
        for c in sorted(used_consts):
            L.append(f'  n{c} [label="{c}", shape=circle, style=filled, '
                     f'fillcolor="#eeeeee"];')
        for gi, g in enumerate(self.gates):
            color = {"MUX": "#ffe0b2", "XOR": "#d1c4e9", "XNOR": "#d1c4e9",
                     "NOT": "#ffcdd2"}.get(g.op, "#bbdefb")
            L.append(f'  g{gi} [label="{g.op}", shape=box, style="rounded,filled", '
                     f'fillcolor="{color}"];')
            for pin, i in enumerate(g.ins):
                port = ["a", "b", "c"][pin] if g.op != "MUX" else ["sel", "1", "0"][pin]
                L.append(f'  n{i} -> g{gi} [label="{port}"];')
            L.append(f'  g{gi} -> n{g.out};')
        L.append("  { rank=sink;")
        for name, nets in self.outputs:
            for k, n in enumerate(nets):
                lbl = name if len(nets) == 1 else f"{name}[{k}]"
                L.append(f'    out_{_ident(name)}_{k} [label="{lbl}", shape=house, '
                         f'style=filled, fillcolor="#f8c9c9"];')
        L.append("  }")
        for name, nets in self.outputs:
            for k, n in enumerate(nets):
                L.append(f'  n{n} -> out_{_ident(name)}_{k};')
        # intermediate nets get a small dot
        shown = set(self.input_nets()) | used_consts
        for g in self.gates:
            if g.out not in shown:
                L.append(f'  n{g.out} [label="", shape=point, width=0.06];')
        L.append("}")
        return "\n".join(L)


def _ident(s: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in s)
