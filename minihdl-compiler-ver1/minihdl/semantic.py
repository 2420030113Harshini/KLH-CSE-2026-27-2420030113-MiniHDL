"""
semantic.py -- Phase 3: Semantic Analysis.

Responsibilities
----------------
1.  Build the block-structured symbol table (global -> module -> when-blocks).
2.  Evaluate compile-time constant expressions (bus widths, indices, shifts).
3.  Infer and annotate the bit-width of every expression node  (type checking
    for a hardware language *is* width checking).
4.  Dataflow checks over the sequential-evaluation semantics of a module body:
        - undeclared / duplicate identifiers
        - assignment to an input port
        - signals that are never driven
        - signals read before they are driven
        - wires that are declared but never used
5.  Structural checks on module instantiation: existence, arity, direction of
    actual arguments, and *recursion detection* over the instantiation graph.

The analyser is deliberately forgiving where hardware practice is forgiving
(width mismatches zero-extend with a warning) and strict where a mistake is
certainly a bug (undeclared name, recursive module).
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set

from .diagnostics import DiagnosticEngine
from .symbols import Scope, Symbol
from . import ast_nodes as A

PHASE = "semantic"

BITWISE = {"&", "|", "^", "~&", "~|", "~^"}
ARITH = {"+", "-"}
COMPARE = {"==", "!="}
SHIFT = {"<<", ">>"}


class SemanticAnalyzer:
    def __init__(self, program: A.Program, diag: DiagnosticEngine):
        self.prog = program
        self.diag = diag
        self.globals = Scope("global")
        self.modules: Dict[str, A.ModuleDecl] = {}
        self.consts: Dict[str, int] = {}
        self.module_scopes: Dict[str, Scope] = {}
        self.inst_graph: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------ run
    def analyze(self) -> None:
        self._collect_globals()
        for m in self.prog.modules:
            self._analyze_module(m)
        self._check_recursion()

    # -------------------------------------------------------------- globals
    def _collect_globals(self):
        for c in self.prog.consts:
            val = self.const_eval(c.value)
            if val is None:
                self.diag.error(PHASE,
                                f"constant '{c.name}' is not a compile-time constant",
                                c.value.span,
                                hint="only literals and other consts may appear here")
                val = 0
            prev = self.globals.declare(
                Symbol(c.name, "const", max(1, val.bit_length()), c.span, val, c))
            if prev:
                self.diag.error(PHASE, f"constant '{c.name}' is already defined",
                                c.span)
            self.consts[c.name] = val

        for m in self.prog.modules:
            prev = self.globals.declare(Symbol(m.name, "module", 0, m.span, None, m))
            if prev:
                self.diag.error(PHASE, f"module '{m.name}' is already defined",
                                m.span,
                                hint=f"previous definition at line {prev.span.line}")
            self.modules[m.name] = m
            self.inst_graph.setdefault(m.name, set())

    # ---------------------------------------------------------- constant eval
    def const_eval(self, e: A.Expr) -> Optional[int]:
        """Fold an expression to an int, or return None if not constant."""
        if isinstance(e, A.Number):
            e.const_value = e.value
            return e.value
        if isinstance(e, A.Ident):
            v = self.consts.get(e.name)
            e.const_value = v
            return v
        if isinstance(e, A.Unary):
            v = self.const_eval(e.operand)
            if v is None:
                return None
            e.const_value = (-v) if e.op == "-" else (~v)
            return e.const_value
        if isinstance(e, A.Binary):
            a, b = self.const_eval(e.left), self.const_eval(e.right)
            if a is None or b is None:
                return None
            try:
                e.const_value = {
                    "+": lambda: a + b, "-": lambda: a - b,
                    "&": lambda: a & b, "|": lambda: a | b, "^": lambda: a ^ b,
                    "~&": lambda: ~(a & b), "~|": lambda: ~(a | b),
                    "~^": lambda: ~(a ^ b),
                    "<<": lambda: a << b, ">>": lambda: a >> b,
                    "==": lambda: int(a == b), "!=": lambda: int(a != b),
                }[e.op]()
            except Exception:
                return None
            return e.const_value
        return None

    def _resolve_type(self, t: A.TypeNode, where: str) -> int:
        if t.kind == "bit":
            t.width = 1
            return 1
        v = self.const_eval(t.width_expr) if t.width_expr else None
        if v is None or v <= 0:
            self.diag.error(PHASE, f"bus width for {where} must be a positive constant",
                            t.span, hint="e.g. bus[8] data;")
            v = 1
        elif v > 64:
            self.diag.error(PHASE, f"bus width {v} exceeds the 64-bit limit", t.span)
            v = 64
        t.width = v
        return v

    # --------------------------------------------------------------- module
    def _analyze_module(self, m: A.ModuleDecl):
        scope = Scope(m.name, self.globals)
        self.module_scopes[m.name] = scope
        self.cur_module = m
        self.cur_scope = scope

        if not m.ports:
            self.diag.warning(PHASE, f"module '{m.name}' has no ports", m.span)

        for p in m.ports:
            w = self._resolve_type(p.type, f"port '{p.name}'")
            sym = Symbol(p.name, p.direction, w, p.span, None, p)
            if p.direction == "input":
                sym.driven = True          # inputs are driven by the environment
            if scope.declare(sym):
                self.diag.error(PHASE, f"duplicate port '{p.name}'", p.span)

        self._walk_block(m.body, scope)

        # --- post-pass dataflow reports -----------------------------------
        for sym in scope.table.values():
            if sym.kind == "output" and not sym.driven:
                self.diag.error(PHASE, f"output '{sym.name}' is never driven",
                                sym.span,
                                hint="assign it somewhere in the module body")
            if sym.kind == "wire" and not sym.driven:
                self.diag.error(PHASE, f"wire '{sym.name}' is never driven", sym.span)
            if sym.kind == "wire" and sym.driven and not sym.read:
                self.diag.warning(PHASE, f"wire '{sym.name}' is never used", sym.span,
                                  hint="dead code elimination will remove it")

    # ------------------------------------------------------------ statements
    def _walk_block(self, blk: A.Block, scope: Scope):
        prev, self.cur_scope = self.cur_scope, scope
        for st in blk.stmts:
            self._walk_stmt(st)
        self.cur_scope = prev

    def _walk_stmt(self, st):
        if isinstance(st, A.WireDecl):
            w = self._resolve_type(st.type, f"wire '{st.name}'")
            sym = Symbol(st.name, "wire", w, st.span, None, st)
            if self.cur_scope.lookup_local(st.name):
                self.diag.error(PHASE, f"'{st.name}' is already declared in this scope",
                                st.span)
            self.cur_scope.declare(sym)
            if st.init is not None:
                rw = self.infer(st.init)
                self._check_assign_width(w, rw, st.name, st.init)
                sym.driven = True

        elif isinstance(st, A.Assign):
            self._walk_assign(st)

        elif isinstance(st, A.Instance):
            self._walk_instance(st)

        elif isinstance(st, A.When):
            cw = self.infer(st.cond)
            if cw > 1:
                self.diag.warning(
                    PHASE, f"'when' condition is {cw} bits wide", st.cond.span,
                    hint="it will be OR-reduced to a single bit")
            self._walk_block(st.then_block, Scope("when@%d" % st.span.line, self.cur_scope))
            if st.else_block is not None:
                self._walk_block(st.else_block,
                                 Scope("else@%d" % st.span.line, self.cur_scope))

        elif isinstance(st, A.Block):
            self._walk_block(st, Scope("block@%d" % st.span.line, self.cur_scope))

    def _walk_assign(self, st: A.Assign):
        lv = st.target
        sym = self.cur_scope.lookup(lv.name)
        if sym is None:
            self.diag.error(PHASE, f"assignment to undeclared signal '{lv.name}'",
                            lv.span, hint="declare it with 'wire' first")
            self.infer(st.value)
            return
        if sym.kind == "input":
            self.diag.error(PHASE, f"cannot assign to input port '{lv.name}'", lv.span,
                            hint="inputs are driven by the enclosing design")
        if sym.kind == "const":
            self.diag.error(PHASE, f"cannot assign to constant '{lv.name}'", lv.span)

        target_w = self._lvalue_width(lv, sym)
        rw = self.infer(st.value)
        self._check_assign_width(target_w, rw, lv.name, st.value)
        sym.driven = True

    def _lvalue_width(self, lv: A.LValue, sym: Symbol) -> int:
        if lv.index is not None:
            idx = self.const_eval(lv.index)
            if idx is None:
                self.diag.error(PHASE, "bit index must be a compile-time constant",
                                lv.index.span)
                return 1
            if not (0 <= idx < sym.width):
                self.diag.error(PHASE,
                                f"bit index {idx} is out of range for "
                                f"'{sym.name}' (width {sym.width})", lv.index.span)
            return 1
        if lv.hi is not None:
            hi, lo = self.const_eval(lv.hi), self.const_eval(lv.lo)
            if hi is None or lo is None:
                self.diag.error(PHASE, "slice bounds must be compile-time constants",
                                lv.span)
                return 1
            if hi < lo:
                self.diag.error(PHASE, f"slice [{hi}:{lo}] has its bounds reversed",
                                lv.span, hint="write it as [high:low]")
                return 1
            if hi >= sym.width:
                self.diag.error(PHASE,
                                f"slice upper bound {hi} exceeds width {sym.width}",
                                lv.span)
            return hi - lo + 1
        return sym.width

    def _check_assign_width(self, lw: int, rw: int, name: str, node: A.Expr):
        if rw > lw:
            self.diag.warning(PHASE,
                              f"assigning {rw} bits to {lw}-bit target '{name}'; "
                              f"upper bits are truncated", node.span)
        elif rw < lw:
            self.diag.warning(PHASE,
                              f"assigning {rw} bits to {lw}-bit target '{name}'; "
                              f"zero-extending", node.span)

    def _walk_instance(self, st: A.Instance):
        target = self.modules.get(st.module_name)
        if target is None:
            self.diag.error(PHASE, f"unknown module '{st.module_name}'", st.span,
                            hint="module declarations may appear in any order")
            for a in st.args:
                self.infer(a)
            return
        self.inst_graph.setdefault(self.cur_module.name, set()).add(st.module_name)

        if len(st.args) != len(target.ports):
            self.diag.error(
                PHASE,
                f"module '{st.module_name}' expects {len(target.ports)} "
                f"port(s) but {len(st.args)} were given", st.span,
                hint="ports are connected positionally: " +
                     ", ".join(p.name for p in target.ports))
            return

        for arg, port in zip(st.args, target.ports):
            pw = port.type.width or 1
            if port.direction == "output":
                lv = as_lvalue(arg)
                if lv is None:
                    self.diag.error(PHASE,
                                    f"argument for output port '{port.name}' must be "
                                    f"a signal, a bit of one, or a slice", arg.span,
                                    hint="e.g. sum, sum[0], or sum[3:0]")
                    continue
                sym = self.cur_scope.lookup(lv.name)
                if sym is None:
                    self.diag.error(PHASE, f"undeclared signal '{lv.name}'", arg.span)
                    continue
                if sym.kind == "input":
                    self.diag.error(PHASE,
                                    f"cannot connect input port '{lv.name}' to an "
                                    f"instance output", arg.span)
                sym.driven = True
                aw = self._lvalue_width(lv, sym)
                arg.width = aw
                if aw != pw:
                    self.diag.warning(PHASE,
                                      f"width mismatch on port '{port.name}': "
                                      f"{pw} vs {aw}", arg.span)
            else:
                aw = self.infer(arg)
                if aw != pw:
                    self.diag.warning(PHASE,
                                      f"width mismatch on port '{port.name}': "
                                      f"expected {pw}, got {aw}", arg.span)

    # ------------------------------------------------ recursion in instances
    def _check_recursion(self):
        WHITE, GREY, BLACK = 0, 1, 2
        color = {m: WHITE for m in self.inst_graph}
        stack: List[str] = []

        def dfs(u: str):
            color[u] = GREY
            stack.append(u)
            for v in sorted(self.inst_graph.get(u, ())):
                if color.get(v, WHITE) == GREY:
                    cyc = " -> ".join(stack[stack.index(v):] + [v])
                    self.diag.error(PHASE,
                                    f"recursive module instantiation: {cyc}",
                                    self.modules[v].span,
                                    hint="hardware cannot be recursively elaborated")
                elif color.get(v, WHITE) == WHITE:
                    dfs(v)
            stack.pop()
            color[u] = BLACK

        for m in list(color):
            if color[m] == WHITE:
                dfs(m)

    # ------------------------------------------------------ width inference
    def infer(self, e: A.Expr) -> int:
        w = self._infer(e)
        e.width = w
        return w

    def _infer(self, e: A.Expr) -> int:
        if isinstance(e, A.Number):
            if e.declared_width:
                return e.declared_width
            return max(1, e.value.bit_length())

        if isinstance(e, A.Ident):
            sym = self.cur_scope.lookup(e.name)
            if sym is None:
                self.diag.error(PHASE, f"undeclared identifier '{e.name}'", e.span,
                                hint="did you forget a 'wire' declaration?")
                return 1
            if sym.kind == "module":
                self.diag.error(PHASE,
                                f"'{e.name}' is a module and cannot be used as a value",
                                e.span)
                return 1
            sym.read = True
            if sym.kind in ("wire", "output") and not sym.driven:
                self.diag.warning(PHASE,
                                  f"'{e.name}' is read before it is driven; "
                                  f"it defaults to 0", e.span)
            if sym.kind == "const":
                e.const_value = sym.value
            return sym.width

        if isinstance(e, A.Unary):
            return self.infer(e.operand)

        if isinstance(e, A.Binary):
            lw, rw = self.infer(e.left), self.infer(e.right)
            if e.op in COMPARE:
                return 1
            if e.op in SHIFT:
                amt = self.const_eval(e.right)
                if amt is None:
                    self.diag.error(PHASE, "shift amount must be a compile-time constant",
                                    e.right.span,
                                    hint="variable shifts need an explicit barrel shifter")
                elif amt < 0:
                    self.diag.error(PHASE, "shift amount must not be negative",
                                    e.right.span)
                return lw
            if lw != rw and lw != 1 and rw != 1:
                self.diag.warning(PHASE,
                                  f"operands of '{e.op}' differ in width "
                                  f"({lw} vs {rw}); the narrower one is zero-extended",
                                  e.span)
            return max(lw, rw)

        if isinstance(e, A.Ternary):
            cw = self.infer(e.cond)
            if cw > 1:
                self.diag.warning(PHASE, f"select condition is {cw} bits; OR-reducing",
                                  e.cond.span)
            aw, bw = self.infer(e.then_e), self.infer(e.else_e)
            if aw != bw:
                self.diag.warning(PHASE,
                                  f"'?:' arms differ in width ({aw} vs {bw})", e.span)
            return max(aw, bw)

        if isinstance(e, A.Index):
            bw = self.infer(e.base)
            idx = self.const_eval(e.index)
            if idx is None:
                self.diag.error(PHASE, "bit index must be a compile-time constant",
                                e.index.span)
            elif not (0 <= idx < bw):
                self.diag.error(PHASE,
                                f"bit index {idx} out of range for a {bw}-bit value",
                                e.index.span)
            return 1

        if isinstance(e, A.SliceExpr):
            bw = self.infer(e.base)
            hi, lo = self.const_eval(e.hi), self.const_eval(e.lo)
            if hi is None or lo is None:
                self.diag.error(PHASE, "slice bounds must be compile-time constants",
                                e.span)
                return 1
            if hi < lo:
                self.diag.error(PHASE, f"slice [{hi}:{lo}] has reversed bounds", e.span)
                return 1
            if hi >= bw:
                self.diag.error(PHASE,
                                f"slice upper bound {hi} exceeds the {bw}-bit value",
                                e.span)
            return hi - lo + 1

        if isinstance(e, A.Concat):
            return sum(self.infer(p) for p in e.parts)

        self.diag.error(PHASE, f"cannot infer a width for {type(e).__name__}", e.span)
        return 1


def as_lvalue(e) -> Optional[A.LValue]:
    """View an expression as an assignable location, or None if it is not one.

    Instance output ports may be connected to `x`, `x[i]` or `x[hi:lo]`.
    """
    if isinstance(e, A.Ident):
        return A.LValue(e.name, span=e.span)
    if isinstance(e, A.Index) and isinstance(e.base, A.Ident):
        return A.LValue(e.base.name, index=e.index, span=e.span)
    if isinstance(e, A.SliceExpr) and isinstance(e.base, A.Ident):
        return A.LValue(e.base.name, hi=e.hi, lo=e.lo, span=e.span)
    return None


def analyze(program, diag):
    sa = SemanticAnalyzer(program, diag)
    sa.analyze()
    return sa
