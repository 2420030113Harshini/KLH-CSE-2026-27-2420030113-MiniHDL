"""
tokens.py -- Token kinds and the Token record produced by the scanner.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from .diagnostics import Span


class T(Enum):
    # --- literals / names -------------------------------------------------
    IDENT = auto()
    NUMBER = auto()

    # --- keywords ---------------------------------------------------------
    MODULE = auto()
    INPUT = auto()
    OUTPUT = auto()
    WIRE = auto()
    BIT = auto()
    BUS = auto()
    CONST = auto()
    WHEN = auto()
    ELSE = auto()

    # --- operators --------------------------------------------------------
    AMP = auto()        # &   and
    PIPE = auto()       # |   or
    CARET = auto()      # ^   xor
    TILDE = auto()      # ~   not
    NAND = auto()       # ~&
    NOR = auto()        # ~|
    XNOR = auto()       # ~^
    EQEQ = auto()       # ==
    NOTEQ = auto()      # !=
    PLUS = auto()       # +
    MINUS = auto()      # -
    SHL = auto()        # <<
    SHR = auto()        # >>
    QUESTION = auto()   # ?
    COLON = auto()      # :
    ASSIGN = auto()     # =

    # --- punctuation ------------------------------------------------------
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACK = auto()
    RBRACK = auto()
    COMMA = auto()
    SEMI = auto()

    EOF = auto()


KEYWORDS = {
    "module": T.MODULE,
    "input": T.INPUT,
    "output": T.OUTPUT,
    "wire": T.WIRE,
    "bit": T.BIT,
    "bus": T.BUS,
    "const": T.CONST,
    "when": T.WHEN,
    "else": T.ELSE,
}

# Ordered longest-first so the scanner performs correct *maximal munch*:
# "~^" must win over "~", "<<" over "<", and so on.
OPERATORS = [
    ("~&", T.NAND), ("~|", T.NOR), ("~^", T.XNOR),
    ("==", T.EQEQ), ("!=", T.NOTEQ),
    ("<<", T.SHL), (">>", T.SHR),
    ("&", T.AMP), ("|", T.PIPE), ("^", T.CARET), ("~", T.TILDE),
    ("!", T.TILDE),
    ("+", T.PLUS), ("-", T.MINUS),
    ("?", T.QUESTION), (":", T.COLON), ("=", T.ASSIGN),
    ("(", T.LPAREN), (")", T.RPAREN),
    ("{", T.LBRACE), ("}", T.RBRACE),
    ("[", T.LBRACK), ("]", T.RBRACK),
    (",", T.COMMA), (";", T.SEMI),
]

# Human-readable names used in parser error messages.
DESCRIBE = {
    T.IDENT: "identifier", T.NUMBER: "number", T.EOF: "end of file",
    T.LPAREN: "'('", T.RPAREN: "')'", T.LBRACE: "'{'", T.RBRACE: "'}'",
    T.LBRACK: "'['", T.RBRACK: "']'", T.COMMA: "','", T.SEMI: "';'",
    T.ASSIGN: "'='", T.COLON: "':'",
}


@dataclass
class Token:
    kind: T
    lexeme: str
    span: Span
    value: Any = None       # int value for NUMBER
    width: int | None = None  # explicit width for sized literals (4'b1010)

    def describe(self) -> str:
        return DESCRIBE.get(self.kind, f"'{self.lexeme}'")

    def __repr__(self) -> str:
        v = "" if self.value is None else f" value={self.value}"
        w = "" if self.width is None else f" width={self.width}"
        return f"<{self.kind.name} {self.lexeme!r} @{self.span}{v}{w}>"
