"""
diagnostics.py -- Error reporting infrastructure.

Provides rustc-style diagnostics: severity, source span, the offending source
line, a caret underline, and an optional hint.  Every compiler phase funnels
its complaints through a single DiagnosticEngine so that the driver can decide
whether compilation may continue.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Color:
    """Minimal ANSI colouriser that can be globally disabled (--no-color)."""
    enabled = True

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GREY = "\033[90m"

    @classmethod
    def paint(cls, text: str, *codes: str) -> str:
        if not cls.enabled or not codes:
            return text
        return "".join(codes) + text + cls.RESET


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass(frozen=True)
class Span:
    """A half-open region of source text, 1-based line, 1-based column."""
    line: int = 0
    col: int = 0
    length: int = 1

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"


NO_SPAN = Span(0, 0, 0)


@dataclass
class Diagnostic:
    severity: Severity
    phase: str
    message: str
    span: Span = NO_SPAN
    hint: Optional[str] = None

    def sort_key(self):
        return (self.span.line, self.span.col)


class CompilerAbort(Exception):
    """Raised when a phase cannot meaningfully continue."""


class DiagnosticEngine:
    def __init__(self, source: str = "", filename: str = "<stdin>"):
        self.filename = filename
        self.lines = source.splitlines()
        self.items: List[Diagnostic] = []

    # ------------------------------------------------------------------ emit
    def emit(self, sev, phase, message, span=NO_SPAN, hint=None):
        self.items.append(Diagnostic(sev, phase, message, span, hint))

    def error(self, phase, message, span=NO_SPAN, hint=None):
        self.emit(Severity.ERROR, phase, message, span, hint)

    def warning(self, phase, message, span=NO_SPAN, hint=None):
        self.emit(Severity.WARNING, phase, message, span, hint)

    def note(self, phase, message, span=NO_SPAN, hint=None):
        self.emit(Severity.NOTE, phase, message, span, hint)

    # ----------------------------------------------------------------- query
    @property
    def errors(self):
        return [d for d in self.items if d.severity is Severity.ERROR]

    @property
    def warnings(self):
        return [d for d in self.items if d.severity is Severity.WARNING]

    def has_errors(self) -> bool:
        return bool(self.errors)

    def abort_if_errors(self, phase: str):
        if self.has_errors():
            raise CompilerAbort(phase)

    # ---------------------------------------------------------------- render
    _SEV_COLOR = {
        Severity.ERROR: (Color.BOLD, Color.RED),
        Severity.WARNING: (Color.BOLD, Color.YELLOW),
        Severity.NOTE: (Color.BOLD, Color.CYAN),
    }

    def render_one(self, d: Diagnostic) -> str:
        colors = self._SEV_COLOR[d.severity]
        head = "{} {}: {}".format(
            Color.paint(d.severity.value, *colors),
            Color.paint("[" + d.phase + "]", Color.GREY),
            Color.paint(d.message, Color.BOLD),
        )
        out = [head]
        if d.span.line > 0:
            loc = f"{self.filename}:{d.span.line}:{d.span.col}"
            gutter = len(str(d.span.line))
            out.append(Color.paint(" " * gutter + "--> ", Color.BLUE) + loc)
            if 0 < d.span.line <= len(self.lines):
                src = self.lines[d.span.line - 1]
                bar = Color.paint(" " * gutter + " | ", Color.BLUE)
                num = Color.paint(f"{d.span.line} | ", Color.BLUE)
                out.append(bar)
                out.append(num + src.replace("\t", " "))
                caret = " " * max(0, d.span.col - 1) + "^" * max(1, d.span.length)
                out.append(bar + Color.paint(caret, *colors))
        if d.hint:
            out.append(Color.paint("  help: ", Color.GREEN) + d.hint)
        return "\n".join(out)

    def render_all(self) -> str:
        if not self.items:
            return ""
        ordered = sorted(self.items, key=Diagnostic.sort_key)
        return "\n\n".join(self.render_one(d) for d in ordered)

    def summary(self) -> str:
        e, w = len(self.errors), len(self.warnings)
        parts = []
        if e:
            parts.append(Color.paint(f"{e} error{'s' if e != 1 else ''}", Color.BOLD, Color.RED))
        if w:
            parts.append(Color.paint(f"{w} warning{'s' if w != 1 else ''}", Color.BOLD, Color.YELLOW))
        if not parts:
            return Color.paint("0 errors, 0 warnings", Color.GREEN)
        return ", ".join(parts)
