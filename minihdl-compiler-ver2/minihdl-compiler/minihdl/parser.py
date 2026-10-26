"""
parser.py -- Phase 2: Syntax Analysis.

A predictive recursive-descent parser for statements/declarations combined
with *precedence climbing* (operator precedence parsing) for expressions.

Error recovery
--------------
On a syntax error the parser enters *panic mode*: it reports the error and
then discards tokens until it reaches a synchronising token (';', '}', or the
start of a new declaration).  This lets one run report many syntax errors
rather than dying on the first.

Grammar (EBNF)
--------------
    program     -> ( constDecl | moduleDecl )*
    constDecl   -> 'const' IDENT '=' expr ';'
    moduleDecl  -> 'module' IDENT '(' [ portList ] ')' block
    portList    -> port ( ',' port )*
    port        -> ('input' | 'output') [ type ] IDENT
    type        -> 'bit' | 'bus' '[' expr ']'
    block       -> '{' stmt* '}'
    stmt        -> wireDecl | assignStmt | instanceStmt | whenStmt | block
    wireDecl    -> 'wire' [ type ] IDENT [ '=' expr ] ';'
    assignStmt  -> lvalue '=' expr ';'
    instanceStmt-> IDENT IDENT '(' [ exprList ] ')' ';'
    whenStmt    -> 'when' '(' expr ')' block [ 'else' (block | whenStmt) ]
    lvalue      -> IDENT [ '[' expr [ ':' expr ] ']' ]

    expr        -> ternary
    ternary     -> orExpr [ '?' expr ':' ternary ]
    orExpr      -> xorExpr   (( '|' | '~|' ) xorExpr)*
    xorExpr     -> andExpr   (( '^' | '~^' ) andExpr)*
    andExpr     -> eqExpr    (( '&' | '~&' ) eqExpr)*
    eqExpr      -> addExpr   (( '==' | '!=' ) addExpr)*
    addExpr     -> unary     (( '+' | '-' | '<<' | '>>' ) unary)*
    unary       -> ('~' | '-') unary | postfix
    postfix     -> primary ( '[' expr [ ':' expr ] ']' )*
    primary     -> NUMBER | IDENT | '(' expr ')' | '{' exprList '}'
"""

from __future__ import annotations
from typing import List, Optional

from .diagnostics import DiagnosticEngine, Span
from .tokens import T, Token
from . import ast_nodes as A

PHASE = "parser"

# Binary operator precedence: higher binds tighter.
PREC = {
    T.PIPE: 1, T.NOR: 1,
    T.CARET: 2, T.XNOR: 2,
    T.AMP: 3, T.NAND: 3,
    T.EQEQ: 4, T.NOTEQ: 4,
    T.PLUS: 5, T.MINUS: 5, T.SHL: 5, T.SHR: 5,
}
OP_TEXT = {
    T.PIPE: "|", T.NOR: "~|", T.CARET: "^", T.XNOR: "~^",
    T.AMP: "&", T.NAND: "~&", T.EQEQ: "==", T.NOTEQ: "!=",
    T.PLUS: "+", T.MINUS: "-", T.SHL: "<<", T.SHR: ">>",
}
SYNC = {T.SEMI, T.RBRACE, T.MODULE, T.CONST, T.WIRE, T.WHEN, T.EOF}


class _PanicError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token], diag: DiagnosticEngine):
        self.toks = tokens
        self.p = 0
        self.diag = diag

    # ------------------------------------------------------------ utilities
    def peek(self, k: int = 0) -> Token:
        j = min(self.p + k, len(self.toks) - 1)
        return self.toks[j]

    @property
    def cur(self) -> Token:
        return self.peek()

    def at(self, *kinds) -> bool:
        return self.cur.kind in kinds

    def advance(self) -> Token:
        t = self.cur
        if t.kind is not T.EOF:
            self.p += 1
        return t

    def match(self, *kinds) -> Optional[Token]:
        if self.at(*kinds):
            return self.advance()
        return None

    def expect(self, kind, what: str = "") -> Token:
        if self.cur.kind is kind:
            return self.advance()
        want = what or _kind_text(kind)
        self.diag.error(PHASE, f"expected {want}, found {self.cur.describe()}",
                        self.cur.span)
        raise _PanicError()

    def synchronise(self):
        while not self.at(T.EOF):
            if self.toks[self.p - 1].kind is T.SEMI:
                return
            if self.cur.kind in SYNC:
                if self.cur.kind in (T.SEMI, T.RBRACE):
                    self.advance()
                return
            self.advance()

    # -------------------------------------------------------------- program
    def parse_program(self) -> A.Program:
        prog = A.Program(span=self.cur.span)
        while not self.at(T.EOF):
            try:
                if self.at(T.CONST):
                    prog.consts.append(self.parse_const())
                elif self.at(T.MODULE):
                    prog.modules.append(self.parse_module())
                else:
                    self.diag.error(
                        PHASE,
                        f"expected 'module' or 'const' at top level, found {self.cur.describe()}",
                        self.cur.span,
                        hint="every statement must live inside a module body")
                    raise _PanicError()
            except _PanicError:
                self.synchronise()
        return prog

    def parse_const(self) -> A.ConstDecl:
        kw = self.expect(T.CONST)
        name = self.expect(T.IDENT, "a constant name")
        self.expect(T.ASSIGN)
        val = self.parse_expr()
        self.expect(T.SEMI)
        return A.ConstDecl(name.lexeme, val, span=kw.span)

    def parse_module(self) -> A.ModuleDecl:
        kw = self.expect(T.MODULE)
        name = self.expect(T.IDENT, "a module name")
        self.expect(T.LPAREN)
        ports: List[A.Port] = []
        if not self.at(T.RPAREN):
            ports.append(self.parse_port())
            while self.match(T.COMMA, T.SEMI):
                if self.at(T.RPAREN):
                    break
                ports.append(self.parse_port())
        self.expect(T.RPAREN)
        body = self.parse_block()
        return A.ModuleDecl(name.lexeme, ports, body, span=kw.span)

    def parse_port(self) -> A.Port:
        d = self.match(T.INPUT, T.OUTPUT)
        if d is None:
            self.diag.error(PHASE,
                            f"expected 'input' or 'output', found {self.cur.describe()}",
                            self.cur.span,
                            hint="every port must state its direction")
            raise _PanicError()
        ty = self.parse_type_opt()
        name = self.expect(T.IDENT, "a port name")
        direction = "input" if d.kind is T.INPUT else "output"
        return A.Port(direction, ty, name.lexeme, span=d.span)

    def parse_type_opt(self) -> A.TypeNode:
        if self.match(T.BIT):
            return A.TypeNode("bit", None, span=self.toks[self.p - 1].span)
        if self.at(T.BUS):
            kw = self.advance()
            self.expect(T.LBRACK)
            w = self.parse_expr()
            self.expect(T.RBRACK)
            return A.TypeNode("bus", w, span=kw.span)
        return A.TypeNode("bit", None, span=self.cur.span)   # implicit 1-bit

    # ----------------------------------------------------------- statements
    def parse_block(self) -> A.Block:
        lb = self.expect(T.LBRACE)
        blk = A.Block([], span=lb.span)
        while not self.at(T.RBRACE, T.EOF):
            try:
                blk.stmts.append(self.parse_stmt())
            except _PanicError:
                self.synchronise()
                if self.at(T.EOF):
                    break
        self.match(T.RBRACE)
        return blk

    def parse_stmt(self):
        if self.at(T.WIRE):
            return self.parse_wire()
        if self.at(T.WHEN):
            return self.parse_when()
        if self.at(T.LBRACE):
            return self.parse_block()
        if self.at(T.IDENT):
            # Two-token lookahead disambiguates `Adder u1(...)` from `x = ...`.
            if self.peek(1).kind is T.IDENT:
                return self.parse_instance()
            return self.parse_assign()
        self.diag.error(PHASE, f"unexpected {self.cur.describe()} in module body",
                        self.cur.span,
                        hint="statements are: wire, assignment, instance, when")
        raise _PanicError()

    def parse_wire(self) -> A.WireDecl:
        kw = self.expect(T.WIRE)
        ty = self.parse_type_opt()
        name = self.expect(T.IDENT, "a wire name")
        init = None
        if self.match(T.ASSIGN):
            init = self.parse_expr()
        self.expect(T.SEMI)
        return A.WireDecl(ty, name.lexeme, init, span=kw.span)

    def parse_assign(self) -> A.Assign:
        lv = self.parse_lvalue()
        self.expect(T.ASSIGN)
        val = self.parse_expr()
        self.expect(T.SEMI)
        return A.Assign(lv, val, span=lv.span)

    def parse_lvalue(self) -> A.LValue:
        name = self.expect(T.IDENT, "a signal name")
        lv = A.LValue(name.lexeme, span=name.span)
        if self.match(T.LBRACK):
            first = self.parse_expr()
            if self.match(T.COLON):
                lv.hi, lv.lo = first, self.parse_expr()
            else:
                lv.index = first
            self.expect(T.RBRACK)
        return lv

    def parse_instance(self) -> A.Instance:
        mod = self.expect(T.IDENT)
        inst = self.expect(T.IDENT, "an instance name")
        self.expect(T.LPAREN)
        args: List[A.Expr] = []
        if not self.at(T.RPAREN):
            args.append(self.parse_expr())
            while self.match(T.COMMA):
                args.append(self.parse_expr())
        self.expect(T.RPAREN)
        self.expect(T.SEMI)
        return A.Instance(mod.lexeme, inst.lexeme, args, span=mod.span)

    def parse_when(self) -> A.When:
        kw = self.expect(T.WHEN)
        self.expect(T.LPAREN)
        cond = self.parse_expr()
        self.expect(T.RPAREN)
        then_b = self.parse_block()
        else_b = None
        if self.match(T.ELSE):
            if self.at(T.WHEN):                      # else-if chain
                inner = self.parse_when()
                else_b = A.Block([inner], span=inner.span)
            else:
                else_b = self.parse_block()
        return A.When(cond, then_b, else_b, span=kw.span)

    # ---------------------------------------------------------- expressions
    def parse_expr(self) -> A.Expr:
        return self.parse_ternary()

    def parse_ternary(self) -> A.Expr:
        cond = self.parse_binary(1)
        if self.match(T.QUESTION):
            a = self.parse_expr()
            self.expect(T.COLON)
            b = self.parse_ternary()        # right associative
            return A.Ternary(cond, a, b, span=cond.span)
        return cond

    def parse_binary(self, min_prec: int) -> A.Expr:
        left = self.parse_unary()
        while True:
            prec = PREC.get(self.cur.kind)
            if prec is None or prec < min_prec:
                return left
            op_tok = self.advance()
            right = self.parse_binary(prec + 1)     # left associative
            left = A.Binary(OP_TEXT[op_tok.kind], left, right, span=op_tok.span)

    def parse_unary(self) -> A.Expr:
        if self.at(T.TILDE, T.MINUS):
            op = self.advance()
            operand = self.parse_unary()
            return A.Unary("~" if op.kind is T.TILDE else "-", operand, span=op.span)
        return self.parse_postfix()

    def parse_postfix(self) -> A.Expr:
        e = self.parse_primary()
        while self.at(T.LBRACK):
            lb = self.advance()
            first = self.parse_expr()
            if self.match(T.COLON):
                lo = self.parse_expr()
                e = A.SliceExpr(e, first, lo, span=lb.span)
            else:
                e = A.Index(e, first, span=lb.span)
            self.expect(T.RBRACK)
        return e

    def parse_primary(self) -> A.Expr:
        t = self.cur
        if t.kind is T.NUMBER:
            self.advance()
            return A.Number(t.value, t.width, span=t.span)
        if t.kind is T.IDENT:
            self.advance()
            return A.Ident(t.lexeme, span=t.span)
        if t.kind is T.LPAREN:
            self.advance()
            e = self.parse_expr()
            self.expect(T.RPAREN)
            return e
        if t.kind is T.LBRACE:
            self.advance()
            parts = [self.parse_expr()]
            while self.match(T.COMMA):
                parts.append(self.parse_expr())
            self.expect(T.RBRACE)
            return A.Concat(parts, span=t.span)
        self.diag.error(PHASE, f"expected an expression, found {t.describe()}", t.span)
        raise _PanicError()


def _kind_text(kind) -> str:
    from .tokens import DESCRIBE
    return DESCRIBE.get(kind, str(kind))


def parse(tokens, diag) -> A.Program:
    return Parser(tokens, diag).parse_program()
