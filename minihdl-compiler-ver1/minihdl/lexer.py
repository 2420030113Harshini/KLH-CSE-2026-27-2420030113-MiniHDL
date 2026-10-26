"""
lexer.py -- Phase 1: Lexical Analysis.

A hand-written scanner (equivalent to the DFA a tool like Flex would build).

Features
--------
*   Maximal-munch operator matching  (`~^` is XNOR, not `~` followed by `^`).
*   Verilog-style sized literals:    4'b1010, 8'hFF, 12'd42, 3'o7
*   Unsized decimal literals:        0, 1, 255
*   Underscore separators inside literals: 8'b1010_1100
*   `//` line comments and *nestable* `/* /* ... */ */` block comments.
*   Panic-free error recovery: an illegal character is reported and skipped,
    so a single typo does not abort the whole scan.
"""

from __future__ import annotations
from typing import List

from .diagnostics import DiagnosticEngine, Span
from .tokens import T, Token, KEYWORDS, OPERATORS

PHASE = "lexer"

_BASES = {"b": 2, "o": 8, "d": 10, "h": 16}
_DIGITS = {
    2: "01", 8: "01234567", 10: "0123456789",
    16: "0123456789abcdefABCDEF",
}


class Lexer:
    def __init__(self, src: str, diag: DiagnosticEngine):
        self.src = src
        self.n = len(src)
        self.i = 0
        self.line = 1
        self.col = 1
        self.diag = diag
        self.out: List[Token] = []

    # -------------------------------------------------------------- helpers
    def _peek(self, k: int = 0) -> str:
        j = self.i + k
        return self.src[j] if j < self.n else "\0"

    def _advance(self) -> str:
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _span(self, line, col, length) -> Span:
        return Span(line, col, length)

    def _add(self, kind, lexeme, line, col, value=None, width=None):
        self.out.append(Token(kind, lexeme, self._span(line, col, len(lexeme)),
                              value, width))

    # ----------------------------------------------------------------- scan
    def scan(self) -> List[Token]:
        while self.i < self.n:
            ch = self._peek()

            if ch in " \t\r\n":
                self._advance()
                continue

            if ch == "/" and self._peek(1) == "/":
                while self.i < self.n and self._peek() != "\n":
                    self._advance()
                continue

            if ch == "/" and self._peek(1) == "*":
                self._block_comment()
                continue

            if ch.isalpha() or ch == "_":
                self._identifier()
                continue

            if ch.isdigit():
                self._number()
                continue

            if self._operator():
                continue

            # ------------------------------------------------ illegal char
            line, col = self.line, self.col
            bad = self._advance()
            self.diag.error(PHASE, f"illegal character {bad!r} in source",
                            Span(line, col, 1),
                            hint="remove it, or did you mean an operator?")

        self.out.append(Token(T.EOF, "<eof>", Span(self.line, self.col, 0)))
        return self.out

    # ------------------------------------------------------------ subroutine
    def _block_comment(self):
        line, col = self.line, self.col
        depth = 0
        while self.i < self.n:
            if self._peek() == "/" and self._peek(1) == "*":
                self._advance(); self._advance(); depth += 1
            elif self._peek() == "*" and self._peek(1) == "/":
                self._advance(); self._advance(); depth -= 1
                if depth == 0:
                    return
            else:
                self._advance()
        self.diag.error(PHASE, "unterminated block comment", Span(line, col, 2),
                        hint="add a matching '*/'")

    def _identifier(self):
        line, col = self.line, self.col
        start = self.i
        while self.i < self.n and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        text = self.src[start:self.i]
        self._add(KEYWORDS.get(text, T.IDENT), text, line, col)

    def _number(self):
        line, col = self.line, self.col
        start = self.i
        while self.i < self.n and (self._peek().isdigit() or self._peek() == "_"):
            self._advance()
        head = self.src[start:self.i].replace("_", "")

        # Sized literal:  WIDTH ' BASE DIGITS
        if self._peek() == "'" and self._peek(1).lower() in _BASES:
            self._advance()                       # consume '
            base_ch = self._advance().lower()     # consume base char
            base = _BASES[base_ch]
            dstart = self.i
            while self.i < self.n and (self._peek() in _DIGITS[base] or self._peek() == "_"):
                self._advance()
            digits = self.src[dstart:self.i].replace("_", "")
            lexeme = self.src[start:self.i]
            if not digits:
                self.diag.error(PHASE, f"sized literal '{lexeme}' has no digits",
                                Span(line, col, len(lexeme)),
                                hint=f"expected base-{base} digits after '{base_ch}")
                self._add(T.NUMBER, lexeme, line, col, 0, 1)
                return
            width = int(head) if head else max(1, int(digits, base).bit_length())
            value = int(digits, base)
            if width <= 0 or width > 64:
                self.diag.error(PHASE, f"literal width {width} out of range 1..64",
                                Span(line, col, len(lexeme)))
                width = max(1, min(64, width))
            if value >= (1 << width):
                self.diag.warning(
                    PHASE,
                    f"literal value {value} does not fit in {width} bit(s); truncating",
                    Span(line, col, len(lexeme)))
                value &= (1 << width) - 1
            self._add(T.NUMBER, lexeme, line, col, value, width)
            return

        # Plain decimal literal (unsized -- width inferred from context).
        self._add(T.NUMBER, head, line, col, int(head), None)

    def _operator(self) -> bool:
        for text, kind in OPERATORS:
            if self.src.startswith(text, self.i):
                line, col = self.line, self.col
                for _ in text:
                    self._advance()
                self._add(kind, text, line, col)
                return True
        return False


def tokenize(src: str, diag: DiagnosticEngine) -> List[Token]:
    return Lexer(src, diag).scan()
