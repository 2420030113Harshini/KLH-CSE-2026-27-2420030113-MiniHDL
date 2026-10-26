"""
ast_nodes.py -- Abstract Syntax Tree.

Every node carries a Span so later phases can produce precise diagnostics.
Semantic analysis annotates expression nodes in-place with `.width`
(the inferred bit-width) and `.const_value` when foldable at compile time.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .diagnostics import Span, NO_SPAN


# ---------------------------------------------------------------- base ------
@dataclass
class Node:
    span: Span = field(default=NO_SPAN, kw_only=True)


@dataclass
class Expr(Node):
    width: Optional[int] = field(default=None, init=False)
    const_value: Optional[int] = field(default=None, init=False)


# ------------------------------------------------------------ expressions ---
@dataclass
class Number(Expr):
    value: int
    declared_width: Optional[int] = None    # None => unsized, adapts to context


@dataclass
class Ident(Expr):
    name: str


@dataclass
class Unary(Expr):
    op: str          # '~' or '-'
    operand: Expr


@dataclass
class Binary(Expr):
    op: str          # & | ^ ~& ~| ~^ == != + - << >>
    left: Expr
    right: Expr


@dataclass
class Ternary(Expr):
    cond: Expr
    then_e: Expr
    else_e: Expr


@dataclass
class Index(Expr):
    base: Expr
    index: Expr


@dataclass
class SliceExpr(Expr):
    base: Expr
    hi: Expr
    lo: Expr


@dataclass
class Concat(Expr):
    parts: List[Expr]    # MSB-first, like Verilog


# -------------------------------------------------------------- types -------
@dataclass
class TypeNode(Node):
    kind: str                 # 'bit' | 'bus'
    width_expr: Optional[Expr] = None
    width: int = 1            # filled in by semantic analysis


# --------------------------------------------------------- declarations -----
@dataclass
class Port(Node):
    direction: str            # 'input' | 'output'
    type: TypeNode
    name: str


@dataclass
class WireDecl(Node):
    type: TypeNode
    name: str
    init: Optional[Expr] = None


@dataclass
class LValue(Node):
    name: str
    index: Optional[Expr] = None
    hi: Optional[Expr] = None
    lo: Optional[Expr] = None


@dataclass
class Assign(Node):
    target: LValue
    value: Expr


@dataclass
class Instance(Node):
    module_name: str
    inst_name: str
    args: List[Expr]


@dataclass
class Block(Node):
    stmts: List[Node] = field(default_factory=list)


@dataclass
class When(Node):
    cond: Expr
    then_block: Block
    else_block: Optional[Block] = None


@dataclass
class ConstDecl(Node):
    name: str
    value: Expr


@dataclass
class ModuleDecl(Node):
    name: str
    ports: List[Port]
    body: Block


@dataclass
class Program(Node):
    modules: List[ModuleDecl] = field(default_factory=list)
    consts: List[ConstDecl] = field(default_factory=list)


# ------------------------------------------------------------- printing -----
_BRANCH, _LAST, _PIPE, _GAP = "+-- ", "\\-- ", "|   ", "    "


def dump_ast(node, prefix: str = "", is_last: bool = True, out=None) -> str:
    """Render the AST as an indented tree (used by --emit ast)."""
    out = [] if out is None else out
    label = _describe(node)
    connector = "" if prefix == "" and out == [] else (_LAST if is_last else _BRANCH)
    out.append(prefix + connector + label)
    child_prefix = prefix + ("" if connector == "" else (_GAP if is_last else _PIPE))
    kids = _children(node)
    for k, child in enumerate(kids):
        dump_ast(child, child_prefix, k == len(kids) - 1, out)
    return "\n".join(out)


def _w(n) -> str:
    return f"  <w={n.width}>" if isinstance(n, Expr) and n.width else ""


def _describe(n) -> str:
    if isinstance(n, Program):
        return "Program"
    if isinstance(n, ModuleDecl):
        return f"Module '{n.name}'"
    if isinstance(n, ConstDecl):
        return f"Const '{n.name}'"
    if isinstance(n, Port):
        return f"Port {n.direction} {n.name} : {_tname(n.type)}"
    if isinstance(n, TypeNode):
        return _tname(n)
    if isinstance(n, Block):
        return "Block"
    if isinstance(n, WireDecl):
        return f"Wire '{n.name}' : {_tname(n.type)}"
    if isinstance(n, Assign):
        return "Assign"
    if isinstance(n, LValue):
        s = f"LValue '{n.name}'"
        return s + ("[...]" if n.index is not None or n.hi is not None else "")
    if isinstance(n, Instance):
        return f"Instance {n.module_name} {n.inst_name}"
    if isinstance(n, When):
        return "When"
    if isinstance(n, Number):
        w = n.declared_width
        return f"Number {n.value}" + (f" ({w}'b)" if w else "") + _w(n)
    if isinstance(n, Ident):
        return f"Ident '{n.name}'" + _w(n)
    if isinstance(n, Unary):
        return f"Unary '{n.op}'" + _w(n)
    if isinstance(n, Binary):
        return f"Binary '{n.op}'" + _w(n)
    if isinstance(n, Ternary):
        return "Ternary '?:'" + _w(n)
    if isinstance(n, Index):
        return "Index" + _w(n)
    if isinstance(n, SliceExpr):
        return "Slice" + _w(n)
    if isinstance(n, Concat):
        return "Concat" + _w(n)
    return type(n).__name__


def _tname(t: TypeNode) -> str:
    return "bit" if t.kind == "bit" else f"bus[{t.width}]"


def _children(n) -> list:
    if isinstance(n, Program):
        return list(n.consts) + list(n.modules)
    if isinstance(n, ModuleDecl):
        return list(n.ports) + [n.body]
    if isinstance(n, ConstDecl):
        return [n.value]
    if isinstance(n, Block):
        return list(n.stmts)
    if isinstance(n, WireDecl):
        return [n.init] if n.init else []
    if isinstance(n, Assign):
        return [n.target, n.value]
    if isinstance(n, LValue):
        return [x for x in (n.index, n.hi, n.lo) if x]
    if isinstance(n, Instance):
        return list(n.args)
    if isinstance(n, When):
        return [n.cond, n.then_block] + ([n.else_block] if n.else_block else [])
    if isinstance(n, Unary):
        return [n.operand]
    if isinstance(n, Binary):
        return [n.left, n.right]
    if isinstance(n, Ternary):
        return [n.cond, n.then_e, n.else_e]
    if isinstance(n, Index):
        return [n.base, n.index]
    if isinstance(n, SliceExpr):
        return [n.base, n.hi, n.lo]
    if isinstance(n, Concat):
        return list(n.parts)
    return []
