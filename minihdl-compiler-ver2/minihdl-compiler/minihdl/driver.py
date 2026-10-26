from __future__ import annotations
import argparse
import copy
import os
import sys
import time
from typing import List

from .diagnostics import DiagnosticEngine, CompilerAbort, Color
from .lexer import tokenize
from .parser import parse
from .semantic import analyze
from .irgen import generate
from .optimizer import Optimizer
from .ast_nodes import dump_ast
from . import codegen, simulator, minimize, timing, testgen

EMITS = ["tokens", "ast", "symbols", "ir", "opt", "verilog", "tb", "c",
         "dot", "json", "truth", "stats", "boolean", "timing", "faults"]


def banner(text: str) -> str:
    line = "=" * 68
    return "\n".join([Color.paint(line, Color.BLUE),
                      Color.paint("  " + text, Color.BOLD, Color.BLUE),
                      Color.paint(line, Color.BLUE)])


class Timer:
    def __init__(self):
        self.marks: List[tuple] = []
        self._t0 = time.perf_counter()

    def mark(self, name: str):
        t = time.perf_counter()
        self.marks.append((name, (t - self._t0) * 1000.0))
        self._t0 = t

    def table(self) -> str:
        total = sum(ms for _, ms in self.marks)
        rows = ["  {:<26} {:>10}".format("phase", "time (ms)"), "  " + "-" * 38]
        for name, ms in self.marks:
            rows.append("  {:<26} {:>10.3f}".format(name, ms))
        rows.append("  " + "-" * 38)
        rows.append("  {:<26} {:>10.3f}".format("total", total))
        return "\n".join(rows)


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mhdlc",
        description="MiniHDL compiler: compiles a digital circuit description "
                    "language down to an optimized gate netlist and Verilog/C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  mhdlc examples/full_adder.hdl --emit all -O2 --verify\n"
               "  mhdlc examples/alu.hdl --top ALU4 --emit verilog,dot -o build\n")
    p.add_argument("source", help="the .hdl file to compile")
    p.add_argument("--top", help="name of the top-level module "
                                 "(default: the last module in the file)")
    p.add_argument("-O", "--opt-level", type=int, default=2, choices=[0, 1, 2],
                   dest="olevel", help="optimization level (default 2)")
    p.add_argument("--emit", default="stats",
                   help="comma-separated list of artefacts, or 'all': "
                        + ", ".join(EMITS))
    p.add_argument("-o", "--outdir", default="build",
                   help="directory for generated files (default: build)")
    p.add_argument("--verify", action="store_true",
                   help="prove the optimizer preserved behaviour by simulation")
    p.add_argument("--truth-limit", type=int, default=12,
                   help="max input bits for truth-table printing (default 12)")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="only print diagnostics and errors")
    p.add_argument("--version", action="version", version="mhdlc 1.0.0")
    return p


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    Color.enabled = sys.stdout.isatty() and not args.no_color

    try:
        with open(args.source, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"mhdlc: cannot read {args.source}: {e.strerror}", file=sys.stderr)
        return 2

    emits = set(EMITS) if args.emit.strip() == "all" else \
        {e.strip() for e in args.emit.split(",") if e.strip()}
    bad = emits - set(EMITS)
    if bad:
        print(f"mhdlc: unknown --emit target(s): {', '.join(sorted(bad))}",
              file=sys.stderr)
        return 2

    diag = DiagnosticEngine(src, os.path.basename(args.source))
    timer = Timer()
    say = (lambda *a: None) if args.quiet else print

    try:
        # ---------------------------------------------------- 1. lexical
        toks = tokenize(src, diag)
        timer.mark("lexical analysis")
        # A bad character is skipped rather than fatal, so scanning continues
        # and the user sees every problem in the file at once.
        if "tokens" in emits:
            say(banner("TOKEN STREAM"))
            for t in toks:
                say("  " + repr(t))

        # ----------------------------------------------------- 2. syntax
        program = parse(toks, diag)
        timer.mark("syntax analysis")
        # Panic-mode recovery leaves a usable (if incomplete) AST, so semantic
        # analysis still runs and reports its own findings before we give up.

        # --------------------------------------------------- 3. semantic
        sema = analyze(program, diag)
        timer.mark("semantic analysis")
        if "ast" in emits:
            say(banner("ABSTRACT SYNTAX TREE"))
            say(dump_ast(program))
        if "symbols" in emits:
            say(banner("SYMBOL TABLE"))
            say(sema.globals.dump())
        diag.abort_if_errors("the front end")

        # ------------------------------------------------- choose top
        if not program.modules:
            print("mhdlc: no modules to compile", file=sys.stderr)
            return 1
        top = args.top or program.modules[-1].name
        if top not in sema.modules:
            print(f"mhdlc: no module named '{top}'. Available: " +
                  ", ".join(sema.modules), file=sys.stderr)
            return 1

        # ------------------------------------------------ 4. IR generation
        netlist = generate(program, sema, diag, top)
        timer.mark("IR generation")
        diag.abort_if_errors("irgen")
        reference = copy.deepcopy(netlist)
        before = netlist.stats()
        if "ir" in emits:
            say(banner(f"UNOPTIMIZED NETLIST  ({before['gates']} gates)"))
            say(netlist.dump())

        # ------------------------------------------------- 5. optimization
        opt = Optimizer(netlist)
        opt.run(args.olevel)
        timer.mark(f"optimization (-O{args.olevel})")
        after = netlist.stats()
        if "opt" in emits:
            say(banner(f"OPTIMIZED NETLIST  ({after['gates']} gates)"))
            say(netlist.dump())

        # ---------------------------------------------------- verification
        if args.verify:
            ok, bad_vec, tested = simulator.check_equivalence(reference, netlist)
            timer.mark("equivalence check")
            say(banner("EQUIVALENCE CHECK"))
            if ok:
                say("  " + Color.paint(
                    f"PASS  optimized netlist matches the reference on "
                    f"{tested} input vector(s)", Color.GREEN, Color.BOLD))
            else:
                say("  " + Color.paint("FAIL  optimizer changed behaviour!",
                                       Color.RED, Color.BOLD))
                say(f"    inputs   : {bad_vec['inputs']}")
                say(f"    reference: {bad_vec['reference']}")
                say(f"    optimized: {bad_vec['optimized']}")
                return 1

        # -------------------------------------------------------- 6. codegen
        os.makedirs(args.outdir, exist_ok=True)
        base = os.path.join(args.outdir, top)
        written = []

        def write(path: str, text: str):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            written.append(path)

        if "verilog" in emits:
            write(base + ".v", codegen.emit_verilog(netlist))
        if "c" in emits:
            write(base + ".c", codegen.emit_c(netlist))
        if "dot" in emits:
            write(base + ".dot", netlist.to_dot())
        if "json" in emits:
            write(base + ".json", codegen.emit_json(netlist))
        if "tb" in emits:
            vecs = _golden_vectors(netlist, limit=64)
            write(base + "_tb.v", codegen.emit_testbench(netlist, vecs))
        timer.mark("target code generation")

        # ----------------------------------------------------------- reports
        if "truth" in emits:
            say(banner("TRUTH TABLE"))
            say(simulator.truth_table(netlist, args.truth_limit))

        if "boolean" in emits:
            say(banner("MINIMIZED BOOLEAN EXPRESSIONS (Quine-McCluskey)"))
            say(minimize.report(netlist))
        if "timing" in emits:
            say(banner("STATIC TIMING ANALYSIS"))
            say(timing.report(netlist))
        if "faults" in emits:
            say(banner("STUCK-AT FAULT ANALYSIS + TEST GENERATION"))
            say(testgen.report(netlist))

        if "stats" in emits:
            say(banner("OPTIMIZATION REPORT"))
            say(opt.report())
            say("")
            say(_stats_table(before, after))

        if written and not args.quiet:
            say(banner("GENERATED FILES"))
            for w in written:
                say("  " + Color.paint(w, Color.GREEN))

    except CompilerAbort as phase:
        print(diag.render_all(), file=sys.stderr)
        print("\n" + Color.paint(f"compilation aborted during {phase}: ",
                                 Color.BOLD) + diag.summary(), file=sys.stderr)
        return 1

    if diag.items:
        print()
        print(diag.render_all())
    if not args.quiet:
        print()
        print(banner("PHASE TIMING"))
        print(timer.table())
        print()
        print("  " + diag.summary())
    return 1 if diag.has_errors() else 0


def _golden_vectors(nl, limit: int):
    """Produce (inputs, expected-outputs) pairs from our own simulator."""
    out = []
    total = sum(len(v) for _, v in nl.inputs)
    if total == 0 or total > 16:
        return out
    widths = [(n, len(v)) for n, v in nl.inputs]
    for bits in range(min(1 << total, limit)):
        assign, shift = {}, 0
        for name, w in widths:
            assign[name] = (bits >> shift) & ((1 << w) - 1)
            shift += w
        out.append((assign, simulator.simulate(nl, assign)))
    return out


def _stats_table(before: dict, after: dict) -> str:
    def row(label, a, b):
        delta = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a:
            pct = (b - a) / a * 100.0
            delta = f"{pct:+6.1f}%"
        return "  {:<18} {:>12} {:>12}   {}".format(label, str(a), str(b), delta)

    lines = ["  {:<18} {:>12} {:>12}   {}".format("metric", "before", "after",
                                                  "change"),
             "  " + "-" * 58,
             row("gates", before["gates"], after["gates"]),
             row("nets", before["nets"], after["nets"]),
             row("area (GE)", before["area_ge"], after["area_ge"]),
             row("critical path", before["depth"], after["depth"]),
             "  " + "-" * 58,
             "  gate mix before : " + _mix(before["by_op"]),
             "  gate mix after  : " + _mix(after["by_op"]),
             "  primary I/O     : {} input bit(s), {} output bit(s)".format(
                 after["inputs"], after["outputs"])]
    return "\n".join(lines)


def _mix(d: dict) -> str:
    return ", ".join(f"{k}x{v}" for k, v in d.items()) if d else "(none)"
