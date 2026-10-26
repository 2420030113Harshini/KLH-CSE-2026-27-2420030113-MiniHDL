"""
api.py -- A one-call programmatic interface to the whole pipeline.

Useful for the test suite, for notebooks, and for anyone who wants to embed
MiniHDL rather than shell out to the command line:

    from minihdl.api import compile_text
    r = compile_text(source, top="FullAdder", olevel=2)
    print(r.netlist.stats(), r.verilog())
"""

from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Optional

from .diagnostics import DiagnosticEngine, CompilerAbort
from .lexer import tokenize
from .parser import parse
from .semantic import analyze
from .irgen import generate
from .optimizer import Optimizer
from . import codegen, simulator


@dataclass
class CompileResult:
    diag: DiagnosticEngine
    program: object = None
    sema: object = None
    netlist: object = None          # optimized
    reference: object = None        # pre-optimization, for equivalence checks
    optimizer: Optional[Optimizer] = None
    ok: bool = False

    # convenience back ends
    def verilog(self) -> str:
        return codegen.emit_verilog(self.netlist)

    def c(self) -> str:
        return codegen.emit_c(self.netlist)

    def dot(self) -> str:
        return self.netlist.to_dot()

    def json(self) -> str:
        return codegen.emit_json(self.netlist)

    def run(self, **inputs) -> dict:
        return simulator.simulate(self.netlist, inputs)

    def equivalent(self):
        return simulator.check_equivalence(self.reference, self.netlist)


def compile_text(src: str, top: Optional[str] = None, olevel: int = 2,
                 filename: str = "<memory>") -> CompileResult:
    diag = DiagnosticEngine(src, filename)
    res = CompileResult(diag)
    try:
        toks = tokenize(src, diag)
        res.program = parse(toks, diag)
        res.sema = analyze(res.program, diag)
        diag.abort_if_errors("front end")
        if not res.program.modules:
            return res
        top = top or res.program.modules[-1].name
        if top not in res.sema.modules:
            diag.error("driver", f"no module named '{top}'")
            return res
        res.netlist = generate(res.program, res.sema, diag, top)
        diag.abort_if_errors("irgen")
        res.reference = copy.deepcopy(res.netlist)
        res.optimizer = Optimizer(res.netlist)
        res.optimizer.run(olevel)
        res.ok = not diag.has_errors()
    except CompilerAbort:
        res.ok = False
    return res
