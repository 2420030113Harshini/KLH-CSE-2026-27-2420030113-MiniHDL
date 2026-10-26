"""
optimizer.py -- Phase 5: Machine-Independent Optimization.

The netlist is repeatedly rewritten until a fixed point is reached.  Passes:

  1. canonicalize      NAND/NOR/XNOR -> {AND,OR,XOR} + NOT, so that later
                       passes only have to reason about a minimal gate basis.
  2. constant folding   AND(x,0)->0, OR(x,1)->1, XOR(x,0)->x, MUX(1,a,b)->a ...
     + algebraic         idempotence  AND(x,x)->x
       simplification    complementation AND(x,~x)->0, XOR(x,~x)->1
                         involution   NOT(NOT(x))->x
  3. copy propagation   removes BUF gates and collapses net aliases via a
                        union-find style `resolve` chain.
  4. CSE                structural hashing with commutativity-aware keys, i.e.
                        AND(a,b) and AND(b,a) hash identically.
  5. DCE                backward reachability from the output nets.
  6. technology mapping (-O2) fuses NOT(AND(a,b)) into a single NAND cell when
                        the inner gate has a fan-out of one -- a peephole pass
                        against a tiny "cell library".

Every pass reports how many gates it removed so `--stats` can show a table.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from .ir import Netlist, Gate, ZERO, ONE

PHASE = "optimizer"
BASE_OPS = {"AND": "NAND", "OR": "NOR", "XOR": "XNOR"}


@dataclass
class PassResult:
    name: str
    iteration: int
    before: int
    after: int

    @property
    def removed(self) -> int:
        return self.before - self.after


class Optimizer:
    def __init__(self, nl: Netlist):
        self.nl = nl
        self.repl: Dict[int, int] = {}
        self.log: List[PassResult] = []

    # ----------------------------------------------------------- net plumbing
    def resolve(self, n: int) -> int:
        seen = []
        while n in self.repl:
            seen.append(n)
            n = self.repl[n]
        for s in seen:
            self.repl[s] = n           # path compression
        return n

    def _rewrite_ports(self):
        self.nl.outputs = [(name, [self.resolve(n) for n in nets])
                           for name, nets in self.nl.outputs]

    # ------------------------------------------------------------------- run
    def run(self, level: int = 2, max_iters: int = 12) -> List[PassResult]:
        if level <= 0:
            return self.log
        self._record("canonicalize", self._canonicalize, 0)
        for it in range(1, max_iters + 1):
            changed = 0
            changed += self._record("const-fold+simplify", self._simplify, it)
            changed += self._record("copy-propagation", self._copy_prop, it)
            changed += self._record("cse", self._cse, it)
            changed += self._record("dce", self._dce, it)
            if changed == 0:
                break
        if level >= 2:
            self._record("tech-map", self._tech_map, 0)
            self._record("dce", self._dce, 0)
        self._rewrite_ports()
        return self.log

    def _record(self, name, fn, it) -> int:
        before = len(self.nl.gates)
        fn()
        self._rewrite_ports()
        after = len(self.nl.gates)
        if before != after or name == "canonicalize":
            self.log.append(PassResult(name, it, before, after))
        return before - after

    # ---------------------------------------------------------- 1 canonicalize
    def _canonicalize(self):
        out: List[Gate] = []
        for g in self.nl.gates:
            base = {"NAND": "AND", "NOR": "OR", "XNOR": "XOR"}.get(g.op)
            if base is None:
                out.append(g)
                continue
            tmp = self.nl.new_net()
            out.append(Gate(base, list(g.ins), tmp, g.label))
            out.append(Gate("NOT", [tmp], g.out, g.label))
        self.nl.gates = out

    # ------------------------------------------- 2 folding + simplification
    def _inverter_map(self) -> Dict[int, int]:
        inv: Dict[int, int] = {}
        for g in self.nl.gates:
            if g.op == "NOT":
                inv[g.out] = g.ins[0]
                inv.setdefault(g.ins[0], g.out)
        inv[ZERO] = inv.get(ZERO, ONE)
        inv[ONE] = ZERO
        return inv

    def _simplify(self):
        inv = self._inverter_map()

        def opposite(a: int, b: int) -> bool:
            return (a == ZERO and b == ONE) or (a == ONE and b == ZERO) or \
                   inv.get(a) == b or inv.get(b) == a

        out: List[Gate] = []
        driver: Dict[int, Gate] = {}
        for g in self.nl.gates:
            ins = [self.resolve(i) for i in g.ins]
            g.ins = ins
            rep: Optional[int] = None
            newg: Optional[Gate] = None

            if g.op == "NOT":
                a = ins[0]
                if a == ZERO:
                    rep = ONE
                elif a == ONE:
                    rep = ZERO
                elif a in driver and driver[a].op == "NOT":
                    rep = driver[a].ins[0]                    # NOT(NOT x) = x

            elif g.op == "BUF":
                rep = ins[0]

            elif g.op == "AND":
                a, b = ins
                if a == ZERO or b == ZERO:
                    rep = ZERO
                elif a == ONE:
                    rep = b
                elif b == ONE:
                    rep = a
                elif a == b:
                    rep = a
                elif opposite(a, b):
                    rep = ZERO

            elif g.op == "OR":
                a, b = ins
                if a == ONE or b == ONE:
                    rep = ONE
                elif a == ZERO:
                    rep = b
                elif b == ZERO:
                    rep = a
                elif a == b:
                    rep = a
                elif opposite(a, b):
                    rep = ONE

            elif g.op == "XOR":
                a, b = ins
                if a == ZERO:
                    rep = b
                elif b == ZERO:
                    rep = a
                elif a == b:
                    rep = ZERO
                elif opposite(a, b):
                    rep = ONE
                elif a == ONE:
                    newg = Gate("NOT", [b], g.out, g.label)
                elif b == ONE:
                    newg = Gate("NOT", [a], g.out, g.label)

            elif g.op == "MUX":
                s, a, b = ins
                if s == ONE:
                    rep = a
                elif s == ZERO:
                    rep = b
                elif a == b:
                    rep = a
                elif a == ONE and b == ZERO:
                    rep = s
                elif a == ZERO and b == ONE:
                    newg = Gate("NOT", [s], g.out, g.label)

            if rep is not None:
                self.repl[g.out] = rep
                continue
            keep = newg if newg is not None else g
            out.append(keep)
            driver[keep.out] = keep
        self.nl.gates = out

    # -------------------------------------------------------- 3 copy propagation
    def _copy_prop(self):
        out = []
        for g in self.nl.gates:
            g.ins = [self.resolve(i) for i in g.ins]
            if g.op == "BUF":
                self.repl[g.out] = g.ins[0]
                continue
            out.append(g)
        self.nl.gates = out

    # ------------------------------------------------------------------ 4 CSE
    def _cse(self):
        seen: Dict[tuple, int] = {}
        out = []
        for g in self.nl.gates:
            g.ins = [self.resolve(i) for i in g.ins]
            k = g.key()
            if k in seen:
                self.repl[g.out] = seen[k]
                continue
            seen[k] = g.out
            out.append(g)
        self.nl.gates = out

    # ------------------------------------------------------------------ 5 DCE
    def _dce(self):
        for g in self.nl.gates:
            g.ins = [self.resolve(i) for i in g.ins]
        self._rewrite_ports()
        live = set(self.resolve(n) for n in self.nl.output_nets())
        drivers = {g.out: g for g in self.nl.gates}
        stack = list(live)
        while stack:
            n = stack.pop()
            g = drivers.get(n)
            if not g:
                continue
            for i in g.ins:
                if i not in live:
                    live.add(i)
                    stack.append(i)
        self.nl.gates = [g for g in self.nl.gates if g.out in live]

    # --------------------------------------------------- 6 technology mapping
    def _tech_map(self):
        for g in self.nl.gates:
            g.ins = [self.resolve(i) for i in g.ins]
        fan = self.nl.fanout()
        drivers = {g.out: g for g in self.nl.gates}
        fused = set()
        out: List[Gate] = []
        for g in self.nl.gates:
            if g.op == "NOT":
                src = drivers.get(g.ins[0])
                if (src is not None and src.op in BASE_OPS
                        and fan.get(src.out, 0) == 1 and src.out not in fused):
                    fused.add(src.out)
                    out.append(Gate(BASE_OPS[src.op], list(src.ins), g.out, g.label))
                    continue
            out.append(g)
        self.nl.gates = [g for g in out if g.out not in fused]

    # --------------------------------------------------------------- report
    def report(self) -> str:
        if not self.log:
            return "  (no optimization performed)"
        rows = ["  {:<22} {:>4} {:>8} {:>8} {:>8}".format(
            "pass", "iter", "before", "after", "removed"),
            "  " + "-" * 54]
        for r in self.log:
            rows.append("  {:<22} {:>4} {:>8} {:>8} {:>8}".format(
                r.name, r.iteration, r.before, r.after, r.removed))
        return "\n".join(rows)


def optimize(nl: Netlist, level: int = 2):
    o = Optimizer(nl)
    o.run(level)
    return o
