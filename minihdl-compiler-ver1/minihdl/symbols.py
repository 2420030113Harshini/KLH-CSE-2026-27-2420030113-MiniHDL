"""
symbols.py -- Symbol table.

A classic block-structured (chained) symbol table: each Scope holds a hash map
and a pointer to its parent.  Lookup walks outwards; insertion always happens
in the innermost scope, which is how shadowing and duplicate detection work.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .diagnostics import Span, NO_SPAN, Color


@dataclass
class Symbol:
    name: str
    kind: str                 # input | output | wire | const | module
    width: int = 1
    span: Span = NO_SPAN
    value: Optional[int] = None      # for consts
    node: object = None              # back-pointer to the declaring AST node
    scope_name: str = "global"
    # dataflow bookkeeping filled in by the semantic analyser
    driven: bool = False
    read: bool = False


class Scope:
    def __init__(self, name: str, parent: Optional["Scope"] = None):
        self.name = name
        self.parent = parent
        self.table: Dict[str, Symbol] = {}
        self.children: List["Scope"] = []
        if parent is not None:
            parent.children.append(self)

    def declare(self, sym: Symbol) -> Optional[Symbol]:
        """Insert; return the previous symbol if this is a redeclaration."""
        prev = self.table.get(sym.name)
        if prev is not None:
            return prev
        sym.scope_name = self.name
        self.table[sym.name] = sym
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.table.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        s: Optional[Scope] = self
        while s is not None:
            hit = s.table.get(name)
            if hit is not None:
                return hit
            s = s.parent
        return None

    # -------------------------------------------------------------- display
    def dump(self, depth: int = 0, out: Optional[List[str]] = None) -> str:
        out = [] if out is None else out
        pad = "  " * depth
        out.append(pad + Color.paint(f"scope '{self.name}'", Color.BOLD, Color.CYAN))
        if not self.table:
            out.append(pad + "  " + Color.paint("(empty)", Color.GREY))
        for sym in self.table.values():
            flags = []
            if sym.driven:
                flags.append("driven")
            if sym.read:
                flags.append("read")
            out.append(
                pad + "  {:<14} {:<8} width={:<3} {:<12} {}".format(
                    sym.name, sym.kind, sym.width,
                    ("=" + str(sym.value)) if sym.value is not None else "",
                    Color.paint(",".join(flags), Color.GREY)))
        for c in self.children:
            c.dump(depth + 1, out)
        return "\n".join(out)
