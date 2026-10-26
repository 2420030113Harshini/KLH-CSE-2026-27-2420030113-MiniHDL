"""
timing.py -- Static timing analysis (STA).

Computes, without simulating anything, when each signal settles:

    arrival(net) = max(arrival(inputs of its driving gate)) + gate delay

then traces the *critical path* backwards from the slowest output and reports
per-output slack against it.  Delays come from GATE_INFO in ir.py (unit-delay
model), so the numbers compare designs rather than predict silicon.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple

from .ir import Netlist, GATE_INFO, ZERO, ONE


def analyze(nl: Netlist) -> dict:
    arrival: Dict[int, int] = {ZERO: 0, ONE: 0}
    pred: Dict[int, Tuple[str, Optional[int]]] = {}
    for n in nl.input_nets():
        arrival[n] = 0
    for g in nl.gates:
        d = GATE_INFO.get(g.op, (0, 1.0, 1))[2]
        worst = max(g.ins, key=lambda i: arrival.get(i, 0))
        arrival[g.out] = arrival.get(worst, 0) + d
        pred[g.out] = (g.op, worst)

    outs = []
    for name, nets in nl.outputs:
        for i, n in enumerate(nets):
            label = name if len(nets) == 1 else f"{name}[{i}]"
            outs.append((label, n, arrival.get(n, 0)))
    delay = max((t for _, _, t in outs), default=0)

    path = []
    if outs:
        net = max(outs, key=lambda o: o[2])[1]
        while True:
            op, prev = pred.get(net, (None, None))
            path.append((nl.net_label(net), op, arrival.get(net, 0)))
            if op is None:
                break
            net = prev
        path.reverse()
    return {"delay": delay, "outputs": outs, "path": path}


def report(nl: Netlist) -> str:
    r = analyze(nl)
    L = [f"  critical path delay : {r['delay']} unit(s)", "", "  critical path:"]
    for k, (label, op, t) in enumerate(r["path"]):
        L.append(f"    {'start ' if op is None else op.ljust(5, ' ') + ' '}"
                 f"-> {label:<14} arrives at t={t}")
    L += ["", f"  {'output':<14} {'arrival':>8} {'slack':>7}", "  " + "-" * 31]
    for label, _, t in r["outputs"]:
        L.append(f"  {label:<14} {t:>8} {r['delay'] - t:>7}")
    fan = nl.fanout()
    if fan:
        n, f = max(fan.items(), key=lambda kv: kv[1])
        L += ["", f"  highest fan-out net : {nl.net_label(n)} drives {f} load(s)"]
    return "\n".join(L)
