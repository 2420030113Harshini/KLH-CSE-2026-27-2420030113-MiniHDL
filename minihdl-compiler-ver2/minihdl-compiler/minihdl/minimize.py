"""
minimize.py -- Two-level logic minimization (Quine-McCluskey).

Given a compiled netlist, derive for every output bit the *minimal
sum-of-products* Boolean expression.  This is the classical exact algorithm:

  1. list the minterms (input rows where the output is 1),
  2. repeatedly merge implicants that differ in exactly one variable,
     leaving the *prime implicants*,
  3. pick the essential primes, then greedily cover what remains.

An implicant is a pair (value, mask): bits set in `mask` are "don't care".
Exact for the sizes it accepts (<= MAX_BITS input bits); the covering step is
greedy, so the result is a minimal-looking cover, not a proven minimum.
"""

from __future__ import annotations
from typing import Dict, List, Tuple

from .ir import Netlist
from .simulator import simulate

MAX_BITS = 8
Implicant = Tuple[int, int]


def var_names(nl: Netlist) -> List[str]:
    names = []
    for name, nets in nl.inputs:
        names += [name if len(nets) == 1 else f"{name}[{i}]" for i in range(len(nets))]
    return names


def _assign(nl: Netlist, row: int) -> Dict[str, int]:
    out, shift = {}, 0
    for name, nets in nl.inputs:
        out[name] = (row >> shift) & ((1 << len(nets)) - 1)
        shift += len(nets)
    return out


def prime_implicants(minterms: List[int]) -> List[Implicant]:
    terms = {(m, 0) for m in minterms}
    primes = set()
    while terms:
        used, nxt = set(), set()
        ordered = sorted(terms)
        for i, (v1, m1) in enumerate(ordered):
            for v2, m2 in ordered[i + 1:]:
                d = v1 ^ v2
                if m1 == m2 and d and d & (d - 1) == 0:
                    nxt.add((v1 & ~d, m1 | d))
                    used.update({(v1, m1), (v2, m2)})
        primes |= terms - used
        terms = nxt
    return sorted(primes)


def _covers(p: Implicant, m: int) -> bool:
    return (m & ~p[1]) == p[0]


def minimal_cover(minterms: List[int]) -> List[Implicant]:
    primes = prime_implicants(minterms)
    chosen: List[Implicant] = []
    for m in minterms:                              # essential primes
        cands = [p for p in primes if _covers(p, m)]
        if len(cands) == 1 and cands[0] not in chosen:
            chosen.append(cands[0])
    left = {m for m in minterms if not any(_covers(p, m) for p in chosen)}
    while left:                                     # greedy cover of the rest
        best = max(primes, key=lambda p: (sum(_covers(p, m) for m in left),
                                          bin(p[1]).count("1")))
        chosen.append(best)
        left = {m for m in left if not _covers(best, m)}
    return chosen


def term_text(p: Implicant, names: List[str]) -> str:
    lits = []
    for k, n in enumerate(names):
        if not (p[1] >> k) & 1:
            lits.append(n if (p[0] >> k) & 1 else "~" + n)
    return " & ".join(lits) if lits else "1"


def cover_text(cover: List[Implicant], names: List[str], total: int) -> str:
    if not cover:
        return "0"
    return " | ".join(term_text(p, names) for p in cover)


def eval_cover(cover: List[Implicant], row: int) -> int:
    return int(any(_covers(p, row) for p in cover))


def minimize(nl: Netlist) -> Dict[str, List[Implicant]]:
    """Return {output-bit-label: cover}. Raises ValueError if too wide."""
    total = sum(len(n) for _, n in nl.inputs)
    if total > MAX_BITS:
        raise ValueError(f"{total} input bits exceeds the {MAX_BITS}-bit limit")
    rows = [simulate(nl, _assign(nl, r)) for r in range(1 << total)]
    result: Dict[str, List[Implicant]] = {}
    for name, nets in nl.outputs:
        for i in range(len(nets)):
            label = name if len(nets) == 1 else f"{name}[{i}]"
            ones = [r for r in range(1 << total) if (rows[r][name] >> i) & 1]
            result[label] = minimal_cover(ones)
    return result


def report(nl: Netlist) -> str:
    try:
        covers = minimize(nl)
    except ValueError as e:
        return f"  skipped: {e}"
    names = var_names(nl)
    total = len(names)
    lines = []
    for label, cover in covers.items():
        full = len(cover) == 1 and cover[0][1] == (1 << total) - 1
        text = "1" if full else cover_text(cover, names, total)
        lits = 0 if full else sum(total - bin(p[1]).count("1") for p in cover)
        lines.append(f"  {label:<10} = {text}")
        lines.append(f"  {'':<10}   ({len(cover)} product term(s), {lits} literal(s))")
    return "\n".join(lines)
