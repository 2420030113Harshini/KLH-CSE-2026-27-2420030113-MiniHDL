# Prompt for a project builder (Lovable / Bolt / Replit / v0 / Cursor)

Copy everything between the two lines into the builder. If it accepts file
uploads, also attach the `minihdl/` folder and `examples/` from the project zip.

---

## ROLE AND GOAL

Build **MiniHDL Studio**, a full-stack web application: an online IDE and
visualizer for **MiniHDL**, a small combinational hardware description
language. A user writes a digital circuit, presses Compile, and sees every
stage of a real compiler: diagnostics, the optimized gate-level schematic with
live signal values, an optimizer before/after report, minimized Boolean
equations, static timing, fault coverage with generated test vectors, and
generated Verilog. The audience is computer-engineering students and the
examiners marking a Compiler Design project, so correctness and clarity matter
more than flash. It must feel like a precise engineering instrument.

## TECH STACK

- Frontend: React 18 + TypeScript + Vite, plain CSS variables (no heavy UI kit),
  CodeMirror 6 for the editor.
- Backend (preferred): Python 3.10+ with FastAPI, importing the uploaded
  `minihdl` package unchanged. One function does all the work:
  `minihdl.api.compile_text(source, top, olevel)` returns an object with
  `.ok`, `.diag.items`, `.program`, `.netlist`, `.reference`, `.optimizer`,
  `.tokens`, and helpers `.verilog()`, `.c()`, `.equivalent()`.
- Backend (fallback if Python cannot run in this environment): re-implement the
  pipeline in TypeScript following the language spec below, and keep the same
  JSON contract so the frontend does not change.
- No database and no authentication are required. Saved circuits live in
  `localStorage` (try/catch every access).

## THE LANGUAGE (for the editor and the fallback compiler)

```
const WIDTH = 4;
module FullAdder(input a, input b, input cin, output sum, output cout) {
    wire s1 = a ^ b;
    sum  = s1 ^ cin;
    cout = (a & b) | (s1 & cin);
}
```
- Types: `bit` (default) and `bus[N]`. Literals: `5`, `4'b1010`, `8'hFF`, `12'd42`, `_` allowed.
- Operators, loosest to tightest: `?:`, `| ~|`, `^ ~^`, `& ~&`, `== !=`, `+ - << >>`, unary `~ -`, postfix `[i]` `[hi:lo]`. Concatenation `{a, b}` is MSB-first.
- Statements: `wire`, assignment, `when (c) {...} else when (c) {...} else {...}`, module instantiation `FullAdder u0(a, b, c, s, co);` (positional ports), blocks.
- Semantics: a module body is evaluated sequentially; a later assignment overrides an earlier one; `when` becomes multiplexers. Combinational only (no clocks).
- Comments: `//` and nestable `/* */`.
- Keywords for syntax highlighting: module input output wire bit bus const when else.

## API CONTRACT (implement exactly)

`GET /api/examples` returns `[{name, source}]`.

`POST /api/compile` with `{source: string, top?: string, olevel: 0|1|2}` returns:

```json
{
  "ok": true,
  "top": "FullAdder",
  "modules": ["HalfAdder", "FullAdder"],
  "diagnostics": [{"severity":"error|warning|note","phase":"semantic","message":"...","line":12,"col":5,"length":3,"hint":"..."}],
  "netlist": {"name":"FullAdder",
              "inputs":[{"name":"a","bits":[2]}],
              "outputs":[{"name":"sum","bits":[11]}],
              "gates":[{"op":"XOR","in":[2,3],"out":5}]},
  "before": {"gates":5,"area_ge":12.0,"depth":4,"nets":10,"by_op":{"AND":2}},
  "after":  {"gates":5,"area_ge":12.0,"depth":4,"nets":10,"by_op":{"AND":2}},
  "equivalence": {"ok": true, "tested": 8},
  "coverage": {"percent": 100.0, "tests": 3, "faults": 16},
  "timing": 4,
  "texts": {"Verilog":"...", "C model":"...", "Optimizer":"...", "Boolean":"...",
            "Timing":"...", "Faults":"...", "Truth table":"...",
            "Netlist before":"...", "Netlist after":"...", "AST":"...", "Tokens":"..."}
}
```
Net ids 0 and 1 are the constants 0 and 1. Gate ops: AND OR XOR NAND NOR XNOR
NOT BUF MUX. `MUX(sel, a, b)` yields `a` when sel is 1, otherwise `b`. Gates
arrive in topological order. When `ok` is false, `netlist` is absent and
`texts` may hold only Tokens and AST. Never return ANSI escape codes.

## SCREENS AND FEATURES

One screen, two panes, plus a header. Responsive: stacks vertically under 860px.

1. **Header**: product name, Example picker, Top-module picker (filled from
   `modules`), Optimization picker (-O0 / -O1 / -O2), primary Compile button.
   Ctrl/Cmd+Enter compiles.
2. **Editor pane (left)**: CodeMirror with MiniHDL highlighting, line numbers,
   error squiggles from `diagnostics`. Below it a diagnostics list; clicking an
   item jumps to and selects the offending range. Empty state: "Compiled with
   no errors or warnings."
3. **Results pane (right)**:
   - **Summary strip**: gates before → after, area before → after, critical
     path before → after, equivalence PASS/FAIL with vector count, fault
     coverage percent with test count.
   - **Tabs**: Circuit, Optimizer, Boolean, Timing, Faults, Truth table,
     Verilog, C model, Netlist before, Netlist after, AST, Tokens.
   - **Circuit tab (the centerpiece)**: SVG schematic generated from
     `netlist`. Columns are logic depth (inputs at depth 0, outputs at the
     right). Gates are labelled boxes, inputs/outputs are pills, wires are
     curves. **Every input is clickable and flips between 0 and 1; all wires
     and gates recompute in the browser and turn the "high" colour when their
     value is 1.** Buttons: All 0, Random, Step +1 (binary counter over all
     input bits). A readout shows e.g. `a=5 b=3  →  sum=8`. Evaluate in
     JavaScript with the gate semantics above.
   - **Optimizer tab**: before/after table plus per-pass gate removal.
   - **Faults tab**: coverage, any undetectable (redundant) faults, and the
     generated test vectors; a button "Apply test" loads a vector into the
     Circuit tab inputs.
   - Code tabs have a Copy button and a Download button (`.v`, `.c`).
4. **Compare mode** (extra credit): toggle to show the -O0 and -O2 schematics
   side by side so the gate reduction is visible.
5. **Saved circuits**: Save/Load/Delete named circuits in `localStorage`.

## DESIGN DIRECTION

A drafting-table feel: pale blue-grey vellum background, deep navy ink, one
teal "signal high" colour, muted slate for "signal low", vermilion only for
errors. Dark mode (prefers-color-scheme) inverts to a deep navy blueprint with
pale lines and a bright teal signal. Typography: a book serif (Iowan Old
Style / Palatino / Georgia) for UI text, a programmer monospace (Cascadia Code
/ Consolas / Menlo) for code and data. The live schematic is the one memorable
element; keep everything else quiet. No gradients, no emoji, no decorative
cards, sentence-case labels, copy that states what happens ("Compile",
"Apply test"). Visible keyboard focus, `aria-label` on schematic inputs,
respect `prefers-reduced-motion`, text contrast at least 4.5:1.

## ERROR AND EMPTY STATES

- Server unreachable: "Cannot reach the server. Check that it is running."
- Compile errors: Circuit tab explains there is no circuit yet and points to
  the diagnostics list; summary strip shows the error count.
- Module has more than 8 input bits: the Boolean tab shows "skipped" text from
  the server; do not treat it as a failure.
- Very large netlists (over 400 gates): render the schematic inside a scroll
  container; never freeze the page.

## SAMPLE DATA (pre-load these as examples)

Use the five files in `examples/`: `adder.hdl` (HalfAdder, FullAdder,
RippleCarry4), `alu.hdl` (ALU4), `datapath.hdl` (Mux4, Decoder2to4,
PriorityEncoder, Datapath), `optimize_demo.hdl` (Redundant), `errors.hdl`
(deliberately broken; shows 13 diagnostics). Default to `adder.hdl`.

## ACCEPTANCE CRITERIA

1. Compiling `adder.hdl` with top `FullAdder` shows 5 gates, equivalence PASS
   on 8 vectors, and 100% fault coverage with 3 tests.
2. Compiling `optimize_demo.hdl`, top `Redundant`, at -O0 then -O2 shows gates
   dropping from about 23 to 2, and fault coverage rising from 57.7% to 100%.
3. In the Circuit tab for FullAdder, setting a=1 b=1 cin=0 reads `sum=0 cout=1`.
4. `errors.hdl` shows red diagnostics; clicking one selects the exact source range.
5. Changing the Top-module picker recompiles without losing the editor text.
6. The page works at 375px width and in both light and dark mode.
7. No console errors; no ANSI codes in any displayed text.

## NON-GOALS

Sequential logic (flip-flops, clocks), user accounts, collaboration, and
deploying to real FPGAs. Mention "combinational only" in an About note.

## DELIVERABLES

Working app with a README containing install and run commands, the API
contract above, and a short architecture diagram.

---

## Tips for using this prompt

- Builders that cannot run Python will take the fallback path and port the
  compiler to TypeScript. That is a large task, so ask for it in stages:
  "first the lexer and parser, then semantic analysis, then the netlist
  generator, then the optimizer".
- Always attach the `minihdl/` folder if the platform allows it; the backend
  then needs only a thin FastAPI wrapper (see `server.py` for the exact
  response-building code you can paste in).
- After the first build, test the acceptance criteria one by one and report
  failures back to the builder by number.
