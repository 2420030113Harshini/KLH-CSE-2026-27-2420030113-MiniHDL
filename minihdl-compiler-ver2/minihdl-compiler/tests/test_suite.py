#!/usr/bin/env python3
"""
test_suite.py -- regression tests for every phase of the MiniHDL compiler.

Run from the project root:

    python tests/test_suite.py

Each test is a plain function; there is no external dependency so the suite
runs anywhere Python 3.10+ runs.
"""

from __future__ import annotations
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minihdl.api import compile_text                       # noqa: E402
from minihdl.diagnostics import DiagnosticEngine, Color     # noqa: E402
from minihdl.lexer import tokenize                          # noqa: E402
from minihdl.tokens import T                                # noqa: E402
from minihdl import simulator, minimize, timing, testgen    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")

_tests = []


def test(fn):
    _tests.append(fn)
    return fn


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def load(name: str) -> str:
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------- lexer
@test
def test_maximal_munch():
    """'~^' must scan as one XNOR token, not '~' then '^'."""
    d = DiagnosticEngine("a ~^ b ~& c ~| d")
    kinds = [t.kind for t in tokenize("a ~^ b ~& c ~| d", d)]
    check(T.XNOR in kinds and T.NAND in kinds and T.NOR in kinds,
          f"maximal munch failed: {kinds}")
    check(T.CARET not in kinds, "'^' should have been absorbed into '~^'")


@test
def test_sized_literals():
    d = DiagnosticEngine("")
    toks = tokenize("4'b1010 8'hFF 12'd42 3'o7 255 8'b1010_1100", d)
    nums = [(t.value, t.width) for t in toks if t.kind is T.NUMBER]
    check(nums == [(10, 4), (255, 8), (42, 12), (7, 3), (255, None), (172, 8)],
          f"bad literal scan: {nums}")
    check(not d.has_errors(), "literals should scan cleanly")


@test
def test_nested_block_comment():
    d = DiagnosticEngine("")
    toks = tokenize("/* outer /* inner */ still outer */ a", d)
    check([t.kind for t in toks] == [T.IDENT, T.EOF], "nested comments broken")


@test
def test_illegal_char_recovers():
    d = DiagnosticEngine("a @ b")
    toks = tokenize("a @ b", d)
    check(d.has_errors(), "illegal char should be reported")
    check(sum(1 for t in toks if t.kind is T.IDENT) == 2,
          "scanning should continue past a bad character")


# -------------------------------------------------------------------- parser
@test
def test_precedence():
    """'a | b & c' must parse as 'a | (b & c)'."""
    r = compile_text("module M(input a, input b, input c, output y)"
                     "{ y = a | b & c; }", "M", 0)
    check(r.ok, "should compile")
    for bits in range(8):
        a, b, c = bits & 1, (bits >> 1) & 1, (bits >> 2) & 1
        got = r.run(a=a, b=b, c=c)["y"]
        check(got == (a | (b & c)), f"precedence wrong for {a}{b}{c}")


@test
def test_parser_recovers():
    src = ("module M(input a, output y) { y = a @@ ; y = a; }\n"
           "module N(input a, output y) { y = ~a; }\n")
    r = compile_text(src, "N", 0)
    check(r.diag.has_errors(), "syntax errors should be reported")
    check(len(r.diag.errors) >= 1, "at least one error")


# ------------------------------------------------------------------ semantic
@test
def test_undeclared_identifier():
    r = compile_text("module M(input a, output y) { y = a & zzz; }", "M", 0)
    check(any("zzz" in e.message for e in r.diag.errors),
          "undeclared identifier not reported")


@test
def test_assign_to_input():
    r = compile_text("module M(input a, output y) { a = 1'b1; y = a; }", "M", 0)
    check(any("input port" in e.message for e in r.diag.errors),
          "assignment to an input must be rejected")


@test
def test_undriven_output():
    r = compile_text("module M(input a, output y, output q) { y = a; }", "M", 0)
    check(any("never driven" in e.message for e in r.diag.errors),
          "undriven output must be rejected")


@test
def test_recursion_detected():
    r = compile_text("module M(input a, output y) { M u(a, y); }", "M", 0)
    check(any("recursive" in e.message for e in r.diag.errors),
          "recursive instantiation must be rejected")


@test
def test_out_of_range_index():
    r = compile_text("module M(input bus[4] a, output y) { y = a[9]; }", "M", 0)
    check(any("out of range" in e.message for e in r.diag.errors),
          "index range check missing")


# ---------------------------------------------------------------- semantics
@test
def test_full_adder_truth():
    r = compile_text(load("adder.hdl"), "FullAdder", 2)
    check(r.ok, "adder.hdl should compile")
    for bits in range(8):
        a, b, cin = bits & 1, (bits >> 1) & 1, (bits >> 2) & 1
        res = r.run(a=a, b=b, cin=cin)
        total = a + b + cin
        check(res["sum"] == total & 1, f"sum wrong at {bits}")
        check(res["cout"] == total >> 1, f"cout wrong at {bits}")


@test
def test_ripple_carry_adds():
    r = compile_text(load("adder.hdl"), "RippleCarry4", 2)
    check(r.ok, "RippleCarry4 should compile")
    for a in range(16):
        for b in range(16):
            for cin in (0, 1):
                res = r.run(a=a, b=b, cin=cin)
                exp = a + b + cin
                check(res["sum"] == exp & 15 and res["cout"] == (exp >> 4) & 1,
                      f"{a}+{b}+{cin} gave {res}")


@test
def test_alu_operations():
    r = compile_text(load("alu.hdl"), "ALU4", 2)
    check(r.ok, "alu.hdl should compile")
    for a in range(16):
        for b in range(16):
            exp = {0: (a + b) & 15, 1: (a - b) & 15, 2: a & b, 3: a ^ b}
            for op in range(4):
                res = r.run(a=a, b=b, op=op)
                check(res["y"] == exp[op],
                      f"op {op}: {a},{b} -> {res['y']} want {exp[op]}")
                check(res["zero"] == int(exp[op] == 0), "zero flag wrong")
                check(res["eq"] == int(a == b), "eq flag wrong")


@test
def test_shift_and_concat():
    src = """
    module S(input bus[8] d, output bus[8] shl, output bus[8] shr,
             output bus[8] swap) {
        shl  = d << 3;
        shr  = d >> 2;
        swap = {d[3:0], d[7:4]};
    }"""
    r = compile_text(src, "S", 2)
    check(r.ok, "shift module should compile")
    for d in (0, 1, 0x5A, 0xFF, 0x81):
        res = r.run(d=d)
        check(res["shl"] == (d << 3) & 0xFF, f"shl wrong for {d:#x}")
        check(res["shr"] == d >> 2, f"shr wrong for {d:#x}")
        check(res["swap"] == ((d & 0xF) << 4) | (d >> 4), f"swap wrong for {d:#x}")
    check(r.netlist.stats()["gates"] == 0,
          "constant shifts and concatenation must synthesise to zero gates")


@test
def test_priority_encoder():
    r = compile_text(load("datapath.hdl"), "PriorityEncoder", 2)
    check(r.ok, "PriorityEncoder should compile")
    for req in range(16):
        res = r.run(req=req)
        expected = max((i for i in range(4) if req >> i & 1), default=0)
        check(res["code"] == expected, f"req={req:04b} -> {res['code']}")
        check(res["valid"] == int(req != 0), "valid flag wrong")


# ----------------------------------------------------------------- optimizer
@test
def test_optimizer_preserves_semantics():
    cases = [("adder.hdl", "FullAdder"), ("adder.hdl", "RippleCarry4"),
             ("alu.hdl", "ALU4"), ("optimize_demo.hdl", "Redundant"),
             ("datapath.hdl", "Mux4"), ("datapath.hdl", "Decoder2to4"),
             ("datapath.hdl", "PriorityEncoder"), ("datapath.hdl", "Datapath")]
    for fname, top in cases:
        r = compile_text(load(fname), top, 2)
        check(r.ok, f"{fname}:{top} should compile")
        ok, bad, tested = r.equivalent()
        check(ok, f"{top}: optimizer changed behaviour on {bad}")
        check(tested > 0, "no vectors tested")


@test
def test_optimizer_actually_optimizes():
    r = compile_text(load("optimize_demo.hdl"), "Redundant", 2)
    before = r.reference.stats()["gates"]
    after = r.netlist.stats()["gates"]
    check(after <= 3, f"expected <=3 gates after -O2, got {after}")
    check(before > 15, f"unoptimized netlist unexpectedly small ({before})")


@test
def test_olevel_zero_does_nothing():
    a = compile_text(load("optimize_demo.hdl"), "Redundant", 0)
    b = compile_text(load("optimize_demo.hdl"), "Redundant", 2)
    check(a.netlist.stats()["gates"] > b.netlist.stats()["gates"],
          "-O0 should keep more gates than -O2")


@test
def test_cse_merges_identical_logic():
    src = """module M(input a, input b, output x, output y) {
        x = a & b;
        y = b & a;
    }"""
    r = compile_text(src, "M", 2)
    check(r.netlist.stats()["gates"] == 1,
          "commutative CSE should leave exactly one AND gate")


@test
def test_tech_mapping_makes_nand():
    src = "module M(input a, input b, output y) { y = ~(a & b); }"
    r = compile_text(src, "M", 2)
    ops = r.netlist.stats()["by_op"]
    check(ops.get("NAND") == 1 and len(ops) == 1, f"expected one NAND, got {ops}")


# ------------------------------------------------------------------ backends
@test
def test_verilog_backend_shape():
    r = compile_text(load("adder.hdl"), "FullAdder", 2)
    v = r.verilog()
    check("module FullAdder" in v and "endmodule" in v, "verilog skeleton broken")
    check(v.count("assign") >= 3, "expected several assign statements")
    check("input a" in v and "output sum" in v, "ports missing")


@test
def test_c_backend_shape():
    r = compile_text(load("adder.hdl"), "FullAdder", 2)
    c = r.c()
    check("FullAdder_eval" in c and "#include <stdint.h>" in c, "C skeleton broken")


@test
def test_json_backend_parses():
    import json
    r = compile_text(load("alu.hdl"), "ALU4", 2)
    doc = json.loads(r.json())
    check(doc["module"] == "ALU4" and doc["gates"], "json netlist malformed")


@test
def test_dot_backend_shape():
    r = compile_text(load("adder.hdl"), "FullAdder", 2)
    dot = r.dot()
    check(dot.startswith("digraph") and dot.rstrip().endswith("}"),
          "dot output malformed")



# ------------------------------------------------------------ new analyses
@test
def test_quine_mccluskey_is_correct_and_minimal():
    """Covers must reproduce the truth table; full-adder carry is the 3-term majority."""
    for fname, top in [("adder.hdl", "FullAdder"), ("datapath.hdl", "Mux4"),
                       ("datapath.hdl", "Decoder2to4"),
                       ("datapath.hdl", "PriorityEncoder")]:
        nl = compile_text(load(fname), top, 2).netlist
        covers = minimize.minimize(nl)
        total = sum(len(n) for _, n in nl.inputs)
        for row in range(1 << total):
            res = simulator.simulate(nl, minimize._assign(nl, row))
            for name, nets in nl.outputs:
                for i in range(len(nets)):
                    label = name if len(nets) == 1 else f"{name}[{i}]"
                    check(minimize.eval_cover(covers[label], row) == (res[name] >> i) & 1,
                          f"{top}.{label} cover wrong at row {row}")
    fa = minimize.minimize(compile_text(load("adder.hdl"), "FullAdder", 2).netlist)
    check(len(fa["cout"]) == 3, f"cout should minimise to 3 terms, got {len(fa['cout'])}")


@test
def test_quine_mccluskey_refuses_wide_designs():
    nl = compile_text(load("alu.hdl"), "ALU4", 2).netlist
    check("skipped" in minimize.report(nl), "10-bit design should be skipped")


@test
def test_fault_coverage_improves_with_optimization():
    """Redundant logic hides faults; the optimizer removing it restores 100%."""
    raw = testgen.analyze(compile_text(load("optimize_demo.hdl"), "Redundant", 0).netlist)
    opt = testgen.analyze(compile_text(load("optimize_demo.hdl"), "Redundant", 2).netlist)
    check(raw["coverage"] < 100.0 and raw["redundant"], "-O0 should hide faults")
    check(opt["coverage"] == 100.0 and not opt["redundant"], "-O2 should expose all faults")


@test
def test_generated_tests_really_detect_faults():
    """Re-check ATPG independently with the scalar simulator: each fault must be caught."""
    nl = compile_text(load("adder.hdl"), "FullAdder", 2).netlist
    a = testgen.analyze(nl)
    check(a["coverage"] == 100.0 and 0 < len(a["tests"]) < 8, "unexpected test set size")
    for site in [g.out for g in nl.gates]:
        for sv in (0, 1):
            caught = False
            for assign, expect in a["tests"]:
                pat, N, M, _ = testgen._patterns(nl)
                bits = nl.input_nets()
                k, p = 0, {}
                for name, nets in nl.inputs:
                    for i in range(len(nets)):
                        p[bits[k]] = M if (assign[name] >> i) & 1 else 0
                        k += 1
                good = testgen._evaluate(nl, p, M)
                bad = testgen._evaluate(nl, p, M, (site, sv))
                if good != bad:
                    caught = True
                    break
            check(caught, f"net {site} stuck-at-{sv} escaped the generated tests")


@test
def test_timing_agrees_with_netlist_critical_path():
    for fname, top in [("adder.hdl", "RippleCarry4"), ("alu.hdl", "ALU4")]:
        nl = compile_text(load(fname), top, 2).netlist
        r = timing.analyze(nl)
        check(r["delay"] == nl.stats()["depth"], f"{top}: STA disagrees with stats()")
        check(r["path"][0][1] is None and r["path"][-1][2] == r["delay"],
              "critical path must start at an input and end at the slowest output")


# ---------------------------------------------------------- web playground
@test
def test_server_compile_request_success_and_failure():
    from server import compile_request
    ok = compile_request(load("alu.hdl"), "ALU4", 2)
    check(ok["ok"] and ok["equivalence"]["ok"], "ALU4 should compile and verify")
    check(ok["after"]["gates"] < ok["before"]["gates"], "optimizer should shrink the ALU")
    check({"Verilog", "Boolean", "Timing", "Faults"} <= set(ok["texts"]), "missing tabs")
    check("\x1b" not in str(ok), "ANSI colour codes must never reach the browser")
    bad = compile_request(load("errors.hdl"))
    check(not bad["ok"] and len(bad["diagnostics"]) >= 5, "errors.hdl should fail loudly")
    check(all("line" in d and "message" in d for d in bad["diagnostics"]),
          "diagnostics must be structured")
    check(compile_request("x" * 70000)["ok"] is False, "oversized source must be rejected")


@test
def test_server_netlist_json_is_self_contained():
    from server import compile_request
    r = compile_request(load("adder.hdl"), "FullAdder", 2)
    nl = r["netlist"]
    check(nl["inputs"] and nl["outputs"] and nl["gates"], "netlist JSON incomplete")
    check(all(g["op"] and g["in"] for g in nl["gates"]), "gate records incomplete")

# ------------------------------------------------------------------- runner
def main() -> int:
    Color.enabled = sys.stdout.isatty()
    passed = failed = 0
    for fn in _tests:
        name = fn.__name__
        try:
            fn()
            passed += 1
            print(f"  {Color.paint('PASS', Color.GREEN)}  {name}")
        except Exception as exc:
            failed += 1
            print(f"  {Color.paint('FAIL', Color.RED)}  {name}: {exc}")
            if os.environ.get("VERBOSE"):
                traceback.print_exc()
    total = passed + failed
    print()
    print(f"  {passed}/{total} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
