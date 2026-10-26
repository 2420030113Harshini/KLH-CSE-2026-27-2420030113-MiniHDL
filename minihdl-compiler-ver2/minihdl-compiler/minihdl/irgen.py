"""
irgen.py -- Phase 4: Intermediate Code Generation (elaboration / synthesis).

Turns the annotated AST into a flat gate-level netlist.  Four classic compiler
techniques do all the work:

*   **Bit blasting** -- every multi-bit value becomes a *vector of nets*
    (index 0 = LSB).  Operators expand element-wise.
*   **Operator lowering** -- `+`, `-`, `==`, `<<` have no gate equivalent, so
    they are expanded into structures: ripple-carry adders, two's-complement
    negation, XNOR trees, and pure rewiring for constant shifts.
*   **Inlining** -- module instances are elaborated inline (the hardware term
    is *flattening*) with the formal ports bound to the actual argument nets.
*   **SSA-style control merge** -- a `when` statement is lowered by evaluating
    both branches against a snapshot of the environment and then reconciling
    the two versions of each signal with MUX gates: exactly a phi-function.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from .diagnostics import DiagnosticEngine
from .ir import Netlist, ZERO, ONE
from . import ast_nodes as A
from .semantic import as_lvalue

PHASE = "irgen"
INLINE_DEPTH_LIMIT = 32


class Env:
    """A frame of the value environment: signal name -> vector of nets."""

    def __init__(self, parent: Optional["Env"] = None):
        self.vars: Dict[str, List[int]] = {}
        self.parent = parent

    def declare(self, name: str, vec: List[int]):
        self.vars[name] = list(vec)

    def frame_of(self, name: str) -> Optional["Env"]:
        e = self
        while e is not None:
            if name in e.vars:
                return e
            e = e.parent
        return None

    def get(self, name: str) -> Optional[List[int]]:
        f = self.frame_of(name)
        return f.vars[name] if f else None

    def set(self, name: str, vec: List[int]):
        f = self.frame_of(name) or self
        f.vars[name] = list(vec)

    # snapshot / restore support the branch-merge algorithm
    def snapshot(self) -> Dict[Tuple[int, str], Tuple["Env", str, List[int]]]:
        out = {}
        e: Optional[Env] = self
        while e is not None:
            for k, v in e.vars.items():
                out[(id(e), k)] = (e, k, list(v))
            e = e.parent
        return out

    @staticmethod
    def restore(snap):
        for frame, name, vec in snap.values():
            frame.vars[name] = list(vec)


class IRGen:
    def __init__(self, program: A.Program, sema, diag: DiagnosticEngine):
        self.prog = program
        self.sema = sema
        self.diag = diag
        self.modules = sema.modules
        self.consts = sema.consts
        self.nl: Netlist = None          # type: ignore
        self.inline_count = 0

    # ------------------------------------------------------------------ top
    def build(self, top_name: str) -> Netlist:
        top = self.modules[top_name]
        self.nl = Netlist(top_name)
        env = Env()

        for p in top.ports:
            w = p.type.width
            if p.direction == "input":
                nets = [self.nl.new_net(_bitname(p.name, i, w)) for i in range(w)]
                self.nl.add_input(p.name, nets)
                env.declare(p.name, nets)
            else:
                env.declare(p.name, [ZERO] * w)

        self.lower_block(top.body, env, 0)

        for p in top.ports:
            if p.direction == "output":
                vec = env.get(p.name) or [ZERO] * p.type.width
                for i, n in enumerate(vec):
                    self.nl.net_name.setdefault(n, _bitname(p.name, i, len(vec)))
                self.nl.add_output(p.name, vec)
        return self.nl

    # ----------------------------------------------------------- statements
    def lower_block(self, blk: A.Block, env: Env, depth: int):
        inner = Env(env)
        for st in blk.stmts:
            self.lower_stmt(st, inner, depth)

    def lower_stmt(self, st, env: Env, depth: int):
        if isinstance(st, A.WireDecl):
            w = st.type.width
            vec = self.fit(self.lower(st.init, env), w) if st.init else [ZERO] * w
            env.declare(st.name, vec)
            for i, n in enumerate(vec):
                self.nl.net_name.setdefault(n, _bitname(st.name, i, w))

        elif isinstance(st, A.Assign):
            self.lower_assign(st, env)

        elif isinstance(st, A.Instance):
            self.lower_instance(st, env, depth)

        elif isinstance(st, A.When):
            self.lower_when(st, env, depth)

        elif isinstance(st, A.Block):
            self.lower_block(st, env, depth)

    def lower_assign(self, st: A.Assign, env: Env):
        self.store(env, st.target, self.lower(st.value, env))

    def store(self, env: Env, lv: A.LValue, val: List[int]):
        """Write a vector into a whole signal, one bit of it, or a slice."""
        cur = env.get(lv.name)
        if cur is None:
            return                      # already reported by semantic analysis

        if lv.index is not None:
            idx = self.sema.const_eval(lv.index) or 0
            if 0 <= idx < len(cur):
                new = list(cur)
                new[idx] = self.fit(val, 1)[0]
                env.set(lv.name, new)
        elif lv.hi is not None:
            hi = self.sema.const_eval(lv.hi) or 0
            lo = self.sema.const_eval(lv.lo) or 0
            if 0 <= lo <= hi < len(cur):
                new = list(cur)
                new[lo:hi + 1] = self.fit(val, hi - lo + 1)
                env.set(lv.name, new)
        else:
            env.set(lv.name, self.fit(val, len(cur)))

    def lower_when(self, st: A.When, env: Env, depth: int):
        sel = self.reduce_or(self.lower(st.cond, env), st)
        base = env.snapshot()

        self.lower_block(st.then_block, env, depth)
        then_snap = env.snapshot()

        Env.restore(base)
        if st.else_block is not None:
            self.lower_block(st.else_block, env, depth)
        else_snap = env.snapshot()

        Env.restore(base)
        label = f"when@{st.span.line}"
        for key, (frame, name, base_vec) in base.items():
            t_vec = then_snap[key][2]
            e_vec = else_snap[key][2]
            if t_vec == e_vec:
                frame.vars[name] = list(t_vec)
                continue
            merged = []
            for i in range(len(base_vec)):
                a = t_vec[i] if i < len(t_vec) else ZERO
                b = e_vec[i] if i < len(e_vec) else ZERO
                merged.append(a if a == b else self.nl.emit("MUX", [sel, a, b], label))
            frame.vars[name] = merged

    def lower_instance(self, st: A.Instance, env: Env, depth: int):
        target = self.modules.get(st.module_name)
        if target is None:
            return
        if depth >= INLINE_DEPTH_LIMIT:
            self.diag.error(PHASE,
                            f"instantiation nested deeper than {INLINE_DEPTH_LIMIT} "
                            f"levels while inlining '{st.module_name}'", st.span)
            return
        self.inline_count += 1

        frame = Env()
        pending_outputs = []
        for arg, port in zip(st.args, target.ports):
            w = port.type.width
            if port.direction == "input":
                frame.declare(port.name, self.fit(self.lower(arg, env), w))
            else:
                frame.declare(port.name, [ZERO] * w)
                lv = as_lvalue(arg)
                if lv is not None:
                    pending_outputs.append((lv, port.name, w))

        self.lower_block(target.body, frame, depth + 1)

        for lv, port_name, w in pending_outputs:
            vec = self.fit(frame.get(port_name) or [], w)
            for i, n in enumerate(vec):
                self.nl.net_name.setdefault(
                    n, _bitname(f"{st.inst_name}.{port_name}", i, w))
            self.store(env, lv, vec)

    # ---------------------------------------------------------- expressions
    def lower(self, e: A.Expr, env: Env) -> List[int]:
        if isinstance(e, A.Number):
            return self.const_vec(e.value, e.width or 1)

        if isinstance(e, A.Ident):
            vec = env.get(e.name)
            if vec is not None:
                return list(vec)
            if e.name in self.consts:
                return self.const_vec(self.consts[e.name], e.width or 1)
            return [ZERO] * (e.width or 1)

        if isinstance(e, A.Unary):
            v = self.lower(e.operand, env)
            if e.op == "~":
                return [self.g("NOT", [b], e) for b in v]
            return self.add_vec(self.const_vec(0, len(v)), v, invert_b=True,
                                carry_in=ZERO, node=e)   # 0 - v

        if isinstance(e, A.Binary):
            return self.lower_binary(e, env)

        if isinstance(e, A.Ternary):
            sel = self.reduce_or(self.lower(e.cond, env), e)
            a = self.lower(e.then_e, env)
            b = self.lower(e.else_e, env)
            w = max(len(a), len(b))
            a, b = self.fit(a, w), self.fit(b, w)
            return [a[i] if a[i] == b[i] else self.g("MUX", [sel, a[i], b[i]], e)
                    for i in range(w)]

        if isinstance(e, A.Index):
            base = self.lower(e.base, env)
            idx = self.sema.const_eval(e.index) or 0
            return [base[idx]] if 0 <= idx < len(base) else [ZERO]

        if isinstance(e, A.SliceExpr):
            base = self.lower(e.base, env)
            hi = self.sema.const_eval(e.hi) or 0
            lo = self.sema.const_eval(e.lo) or 0
            if 0 <= lo <= hi < len(base):
                return base[lo:hi + 1]
            return [ZERO] * max(1, hi - lo + 1)

        if isinstance(e, A.Concat):
            out: List[int] = []
            for p in reversed(e.parts):          # Verilog concat is MSB-first
                out.extend(self.lower(p, env))
            return out

        return [ZERO]

    def lower_binary(self, e: A.Binary, env: Env) -> List[int]:
        op = e.op
        a = self.lower(e.left, env)

        if op in ("<<", ">>"):                   # constant shift == rewiring
            k = self.sema.const_eval(e.right) or 0
            w = len(a)
            if op == "<<":
                return ([ZERO] * k + a)[:w]
            return self.fit(a[k:], w)

        b = self.lower(e.right, env)

        if op in ("+", "-"):
            w = max(len(a), len(b))
            a, b = self.fit(a, w), self.fit(b, w)
            if op == "+":
                return self.add_vec(a, b, invert_b=False, carry_in=ZERO, node=e)
            return self.add_vec(a, b, invert_b=True, carry_in=ONE, node=e)

        if op in ("==", "!="):
            w = max(len(a), len(b))
            a, b = self.fit(a, w), self.fit(b, w)
            eqbits = [self.g("XNOR", [a[i], b[i]], e) for i in range(w)]
            acc = eqbits[0]
            for x in eqbits[1:]:
                acc = self.g("AND", [acc, x], e)
            return [acc] if op == "==" else [self.g("NOT", [acc], e)]

        gate = {"&": "AND", "|": "OR", "^": "XOR",
                "~&": "NAND", "~|": "NOR", "~^": "XNOR"}[op]
        w = max(len(a), len(b))
        a, b = self.fit(a, w), self.fit(b, w)
        return [self.g(gate, [a[i], b[i]], e) for i in range(w)]

    # -------------------------------------------------------------- helpers
    def g(self, op: str, ins: List[int], node=None) -> int:
        line = getattr(getattr(node, "span", None), "line", 0)
        return self.nl.emit(op, ins, f"line {line}" if line else "")

    def const_vec(self, value: int, width: int) -> List[int]:
        return [ONE if (value >> i) & 1 else ZERO for i in range(max(1, width))]

    def fit(self, vec: List[int], width: int) -> List[int]:
        vec = list(vec)
        if len(vec) >= width:
            return vec[:width]
        return vec + [ZERO] * (width - len(vec))

    def reduce_or(self, vec: List[int], node) -> int:
        if not vec:
            return ZERO
        acc = vec[0]
        for x in vec[1:]:
            acc = self.g("OR", [acc, x], node)
        return acc

    def add_vec(self, a: List[int], b: List[int], invert_b: bool,
                carry_in: int, node) -> List[int]:
        """Ripple-carry adder; with invert_b + carry_in=1 this is a subtractor."""
        carry = carry_in
        result = []
        for i in range(len(a)):
            bi = self.g("NOT", [b[i]], node) if invert_b else b[i]
            p = self.g("XOR", [a[i], bi], node)          # propagate
            s = self.g("XOR", [p, carry], node)          # sum bit
            gen = self.g("AND", [a[i], bi], node)        # generate
            pc = self.g("AND", [p, carry], node)
            carry = self.g("OR", [gen, pc], node)
            result.append(s)
        return result                                    # final carry is dropped


def _bitname(name: str, i: int, width: int) -> str:
    return name if width == 1 else f"{name}[{i}]"


def generate(program, sema, diag, top: str) -> Netlist:
    return IRGen(program, sema, diag).build(top)
