#!/usr/bin/env python3
"""
server.py -- MiniHDL Playground backend.

Serves web/index.html and one JSON endpoint that runs the *real* compiler:

    GET  /                 the playground page
    GET  /api/examples     the example circuits from examples/
    POST /api/compile      {source, top?, olevel?} -> every compiler artefact

Standard library only (http.server), so `python server.py` is all it takes.
Binds to 127.0.0.1: this is a local teaching tool, not a public service.
"""

from __future__ import annotations
import argparse
import glob
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from minihdl.api import compile_text
from minihdl.ast_nodes import dump_ast
from minihdl.diagnostics import Color
from minihdl.driver import _stats_table
from minihdl import codegen, simulator, minimize, timing, testgen

Color.enabled = False                      # JSON must never contain ANSI codes
ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_SOURCE = 64 * 1024


def _diagnostics(diag) -> list:
    out = []
    for d in sorted(diag.items, key=lambda d: d.sort_key()):
        out.append({"severity": d.severity.value, "phase": d.phase,
                    "message": d.message, "line": d.span.line,
                    "col": d.span.col, "length": d.span.length, "hint": d.hint})
    return out


def _netlist_json(nl) -> dict:
    return {"name": nl.name,
            "inputs": [{"name": n, "bits": b} for n, b in nl.inputs],
            "outputs": [{"name": n, "bits": b} for n, b in nl.outputs],
            "gates": [{"op": g.op, "in": g.ins, "out": g.out} for g in nl.gates]}


def compile_request(source: str, top: str | None = None, olevel: int = 2) -> dict:
    """Run the full pipeline and return a JSON-serialisable summary."""
    if len(source) > MAX_SOURCE:
        return {"ok": False, "modules": [], "diagnostics": [{
            "severity": "error", "phase": "server", "line": 0, "col": 0,
            "length": 0, "hint": None,
            "message": f"source is larger than {MAX_SOURCE // 1024} KB"}]}
    r = compile_text(source, top or None, max(0, min(2, int(olevel))))
    resp = {"ok": r.ok, "diagnostics": _diagnostics(r.diag),
            "modules": [m.name for m in r.program.modules] if r.program else []}
    texts = {}
    if r.tokens:
        texts["Tokens"] = "\n".join(
            f"{t.span.line:>3}:{t.span.col:<3} {t.kind.name:<8} {t.lexeme}"
            for t in r.tokens[:600])
    if r.program and r.program.modules:
        try:
            texts["AST"] = dump_ast(r.program)
        except Exception:
            pass
    if r.ok and r.netlist is not None:
        nl, ref = r.netlist, r.reference
        eq, bad, tested = r.equivalent()
        before, after = ref.stats(), nl.stats()
        texts["Optimizer"] = r.optimizer.report() + "\n\n" + _stats_table(before, after)
        texts["Verilog"] = codegen.emit_verilog(nl)
        texts["C model"] = codegen.emit_c(nl)
        texts["Netlist before"] = ref.dump()
        texts["Netlist after"] = nl.dump()
        texts["Truth table"] = simulator.truth_table(nl, 8)
        texts["Boolean"] = minimize.report(nl)
        texts["Timing"] = timing.report(nl)
        fa = testgen.analyze(nl)
        texts["Faults"] = testgen.report(nl)
        resp.update({
            "top": nl.name, "netlist": _netlist_json(nl),
            "names": {str(k): v for k, v in nl.net_name.items()},
            "before": before, "after": after,
            "equivalence": {"ok": eq, "tested": tested},
            "coverage": {"percent": fa["coverage"], "tests": len(fa["tests"]),
                         "faults": fa["total"]},
            "timing": timing.analyze(nl)["delay"]})
    resp["texts"] = texts
    return resp


def list_examples() -> list:
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "examples", "*.hdl"))):
        with open(path, encoding="utf-8") as f:
            out.append({"name": os.path.basename(path), "source": f.read()})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "MiniHDL/1.0"

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(ROOT, "web", "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/examples":
            self._json(200, list_examples())
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/compile":
            return self._send(404, b"not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 2 * MAX_SOURCE:
                return self._json(413, {"error": "request too large"})
            req = json.loads(self.rfile.read(n) or b"{}")
            self._json(200, compile_request(str(req.get("source", "")),
                                            req.get("top"), req.get("olevel", 2)))
        except Exception as e:                        # never kill the server
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description="MiniHDL Playground server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"MiniHDL Playground running at {url}   (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
