# MiniHDL — a compiler for a digital circuit description language

**Compiler Design course project.** `mhdlc` takes a hardware description
written in MiniHDL, runs it through every classical compiler phase, optimizes
the resulting circuit, proves the optimization was safe, and emits synthesisable
Verilog, a C software model, a Graphviz schematic and a JSON netlist.

```
$ python mhdlc.py examples/alu.hdl --top ALU4 --emit all -O2 --verify
```

Written in pure Python 3.10+ with **no third-party dependencies**. Everything —
the scanner, the parser, the optimizer, the simulator — is hand-written, because
the point of the project is to show the machinery rather than hide it behind a
generator.

---

## 1. Why a hardware language?

A circuit description language is an unusually good vehicle for a compiler
project: the back end is a *netlist* instead of assembly, so optimization
becomes visible and checkable. You can literally count the gates before and
after, and you can prove the optimizer correct by exhaustive simulation —
something you cannot do for a C compiler in an afternoon.

---

## 2. Compiler architecture

| # | Phase | Module | Output |
|---|-------|--------|--------|
| 1 | Lexical analysis | `minihdl/lexer.py` | token stream |
| 2 | Syntax analysis | `minihdl/parser.py` | abstract syntax tree |
| 3 | Semantic analysis | `minihdl/semantic.py` | annotated AST + symbol table |
| 4 | Intermediate code generation | `minihdl/irgen.py` | gate-level netlist |
| 5 | Machine-independent optimization | `minihdl/optimizer.py` | smaller netlist |
| 6 | Target code generation | `minihdl/codegen.py` | Verilog / C / DOT / JSON |
| — | Error handling (all phases) | `minihdl/diagnostics.py` | diagnostics |
| — | Symbol management (all phases) | `minihdl/symbols.py` | scoped symbol table |
| — | Verification | `minihdl/simulator.py` | truth tables, equivalence proof |

```
source.hdl
    │  Lexer            maximal munch, sized literals, nested comments
    ▼
  tokens
    │  Parser           recursive descent + precedence climbing,
    ▼                   panic-mode error recovery
   AST
    │  Semantic         scoped symbol table, width inference,
    ▼                   dataflow + recursion checks
 annotated AST
    │  IR generation    bit blasting, operator lowering, inlining,
    ▼                   SSA-style branch merging
 gate netlist  ──────────────────────────── reference copy kept for verification
    │  Optimizer        canonicalise → fold/simplify → copy-prop → CSE → DCE
    ▼                   (to a fixed point) → technology mapping
 optimized netlist
    │  Back ends
    ▼
 Verilog · C · Graphviz · JSON · self-checking testbench
```

### Techniques on display

* **Maximal munch scanning** — `~^` lexes as one XNOR token, never `~` then `^`.
* **Precedence climbing** for expressions, recursive descent for declarations.
* **Panic-mode recovery** — the parser resynchronises on `;` / `}` so one run
  reports every error in the file, not just the first.
* **Block-structured symbol table** with a parent chain, so `when` blocks get
  real nested scopes and shadowing works.
* **Constant-expression folding** at the AST level (bus widths, indices,
  shift amounts must be compile-time constants, and the analyser evaluates them).
* **Type checking as width inference** — in a hardware language, "type" is
  bit-width, and the analyser infers and checks it on every node.
* **Bit blasting** — an 8-bit bus becomes eight single-bit nets.
* **Operator lowering** — `+` expands into a ripple-carry chain, `-` into
  two's-complement add, `==` into an XNOR tree, `<<` into pure rewiring.
* **Inlining / flattening** of module instances, with recursion detection over
  the instantiation graph.
* **SSA-style phi nodes** — `when`/`else` is lowered by snapshotting the value
  environment, elaborating both branches, and merging with MUX gates.
* **A fixed-point optimizer**: constant folding, algebraic identities,
  copy propagation, structural-hashing CSE, dead code elimination.
* **Peephole technology mapping** against a small cell library:
  `NOT(AND(a,b))` fuses to a single `NAND` when the inner gate's fan-out is 1.
* **Translation validation** — `--verify` exhaustively simulates the original
  and optimized netlists against each other and reports any counterexample.

---

## 3. The MiniHDL language

```verilog
const WIDTH = 4;

module FullAdder(input a, input b, input cin, output sum, output cout) {
    wire s1 = a ^ b;
    sum  = s1 ^ cin;
    cout = (a & b) | (s1 & cin);
}

module ALU4(input bus[WIDTH] a, input bus[WIDTH] b, input bus[2] op,
            output bus[WIDTH] y, output zero) {
    wire bus[WIDTH] r;
    r = 4'b0000;

    when (op == 0) { r = a + b; }
    else when (op == 1) { r = a - b; }
    else { r = a ^ b; }

    y    = r;
    zero = ~(r[0] | r[1] | r[2] | r[3]);
}
```

### Grammar (EBNF)

```ebnf
program      ::= ( constDecl | moduleDecl )*
constDecl    ::= 'const' IDENT '=' expr ';'
moduleDecl   ::= 'module' IDENT '(' [ portList ] ')' block
portList     ::= port ( ',' port )*
port         ::= ('input' | 'output') [ type ] IDENT
type         ::= 'bit' | 'bus' '[' expr ']'
block        ::= '{' stmt* '}'
stmt         ::= wireDecl | assignStmt | instanceStmt | whenStmt | block
wireDecl     ::= 'wire' [ type ] IDENT [ '=' expr ] ';'
assignStmt   ::= lvalue '=' expr ';'
instanceStmt ::= IDENT IDENT '(' [ exprList ] ')' ';'
whenStmt     ::= 'when' '(' expr ')' block [ 'else' ( block | whenStmt ) ]
lvalue       ::= IDENT [ '[' expr [ ':' expr ] ']' ]

expr         ::= ternary
ternary      ::= orExpr [ '?' expr ':' ternary ]
orExpr       ::= xorExpr ( ('|' | '~|') xorExpr )*
xorExpr      ::= andExpr ( ('^' | '~^') andExpr )*
andExpr      ::= eqExpr  ( ('&' | '~&') eqExpr  )*
eqExpr       ::= addExpr ( ('==' | '!=') addExpr )*
addExpr      ::= unary   ( ('+' | '-' | '<<' | '>>') unary )*
unary        ::= ('~' | '-') unary | postfix
postfix      ::= primary ( '[' expr [ ':' expr ] ']' )*
primary      ::= NUMBER | IDENT | '(' expr ')' | '{' exprList '}'
```

### Operator precedence (loosest to tightest)

| Level | Operators | Associativity |
|-------|-----------|---------------|
| 1 | `?:` | right |
| 2 | `\|`  `~\|` | left |
| 3 | `^`  `~^` | left |
| 4 | `&`  `~&` | left |
| 5 | `==`  `!=` | left |
| 6 | `+`  `-`  `<<`  `>>` | left |
| 7 | `~`  `-` (unary) | right |
| 8 | `[i]`  `[hi:lo]` (postfix) | left |

### Literals

`0`, `1`, `255` — unsized decimal, width inferred from context.
`4'b1010`, `8'hFF`, `12'd42`, `3'o7` — sized literals, with `_` separators
allowed: `8'b1010_1100`.

### Semantics in one line

A module body is evaluated **sequentially**, like blocking assignments inside a
combinational `always @*` block: a later assignment to a signal supersedes an
earlier one, and `when` merges the two versions with multiplexers. That is what
makes the priority encoder in `examples/datapath.hdl` work.

---

## 4. Using the compiler

```
python mhdlc.py SOURCE.hdl [options]

  --top NAME          top-level module (default: last module in the file)
  -O {0,1,2}          optimization level (default 2)
  --emit LIST         comma-separated, or 'all':
                      tokens, ast, symbols, ir, opt, verilog, tb, c,
                      dot, json, truth, stats
  -o DIR              output directory (default: build)
  --verify            prove the optimizer preserved behaviour
  --truth-limit N     max input bits for truth-table printing (default 12)
  --no-color          plain ASCII output
  -q, --quiet         diagnostics only
```

Common recipes:

```bash
# Everything, for a demo
python mhdlc.py examples/alu.hdl --top ALU4 --emit all -O2 --verify

# Watch the optimizer work
python mhdlc.py examples/optimize_demo.hdl --top Redundant -O0 --emit ir,stats
python mhdlc.py examples/optimize_demo.hdl --top Redundant -O2 --emit opt,stats

# See the error reporting
python mhdlc.py examples/errors.hdl

# Draw the schematic (needs Graphviz)
python mhdlc.py examples/adder.hdl --top FullAdder --emit dot
dot -Tsvg build/FullAdder.dot -o FullAdder.svg

# Run the regression suite
python tests/test_suite.py
```

---

## 5. Sample output

Optimizing `examples/optimize_demo.hdl`:

```
  pass                   iter   before    after  removed
  ------------------------------------------------------
  canonicalize              0       23       23        0
  const-fold+simplify       1       23       12       11
  cse                       1       12        9        3
  dce                       1        9        4        5
  const-fold+simplify       2        4        2        2

  metric                   before        after   change
  ----------------------------------------------------------
  gates                        23            2    -91.3%
  nets                         28           28     +0.0%
  area (GE)                  47.0          5.0    -89.4%
  critical path                 4            2    -50.0%

  PASS  optimized netlist matches the reference on 8 input vector(s)
```

A diagnostic:

```
error [semantic]: bit index 9 out of range for a 4-bit value
  --> errors.hdl:14:17
   |
14 |     wire t2 = b[9];
   |                 ^
```

---

## 6. Examples supplied

| File | Modules | Shows off |
|------|---------|-----------|
| `examples/adder.hdl` | `HalfAdder`, `FullAdder`, `RippleCarry4` | hierarchy, inlining, buses |
| `examples/alu.hdl` | `ALU4` | constants, `when` chains, `+` `-` `==`, reduction |
| `examples/datapath.hdl` | `Mux4`, `Decoder2to4`, `PriorityEncoder`, `Datapath` | `?:`, concatenation, shifts, nested `when` |
| `examples/optimize_demo.hdl` | `Redundant` | every optimizer rule, 23 gates → 2 |
| `examples/errors.hdl` | `Broken`, `Cyclic` | 10 different diagnostics in one run |

---

## 7. Project layout

```
minihdl-compiler/
├── mhdlc.py                 entry point
├── Makefile                 make demo / test / clean
├── README.md
├── minihdl/
│   ├── diagnostics.py       spans, severities, caret rendering
│   ├── tokens.py            token kinds, keyword and operator tables
│   ├── lexer.py             phase 1
│   ├── ast_nodes.py         AST + tree printer
│   ├── parser.py            phase 2
│   ├── symbols.py           scoped symbol table
│   ├── semantic.py          phase 3
│   ├── ir.py                netlist IR, stats, Graphviz export
│   ├── irgen.py             phase 4
│   ├── optimizer.py         phase 5
│   ├── codegen.py           phase 6 back ends
│   ├── simulator.py         truth tables + equivalence checking
│   ├── api.py               one-call programmatic interface
│   └── driver.py            CLI, phase sequencing, timing
├── examples/*.hdl
└── tests/test_suite.py      32 regression tests
```

---

## 8. Questions you are likely to be asked

**Where is the intermediate representation?** `minihdl/ir.py`. A gate is
`out = OP in0, in1`, which is three-address code; the netlist is the flow graph.

**Which optimizations are machine-independent?** Constant folding, algebraic
simplification, copy propagation, CSE and DCE. Technology mapping (`-O2`) is
the machine-dependent one: it targets a specific cell library.

**How do you know the optimizer is correct?** `--verify` keeps a deep copy of
the pre-optimization netlist and compares the two by simulation — exhaustively
up to 16 input bits, then by 4096 pseudo-random vectors. This is translation
validation, and the test suite runs it on every example.

**What about left recursion?** The expression grammar is left-recursive on
paper; precedence climbing implements left association iteratively inside
`parse_binary`, so no left recursion reaches the recursive-descent machinery.

**Why no code for flip-flops / clocks?** MiniHDL is deliberately combinational.
Sequential logic would need latch inference and a clock domain model, which is a
second project. The `when` merge already builds the multiplexer structure a
sequential extension would reuse.

**Is the symbol table one table or many?** Many, chained: one global scope, one
per module, and one per `when` / `else` / nested block. Lookup walks outwards;
insertion is always innermost.

---

## 9. Requirements

Python 3.10 or newer. Optional: Graphviz (`dot`) to render schematics, and
Icarus Verilog (`iverilog`) to run the generated testbench.

---

## 10. Advanced features (v1.1)

Beyond the six compiler phases, MiniHDL now includes the analyses a real
EDA flow runs after synthesis, plus a browser front end.

| Feature | Module | Command |
|---|---|---|
| **Quine–McCluskey Boolean minimisation** — exact minimal sum-of-products per output bit | `minimize.py` | `--emit boolean` |
| **Static timing analysis** — arrival times, traced critical path, per-output slack, worst fan-out | `timing.py` | `--emit timing` |
| **Stuck-at fault simulation + automatic test-pattern generation** — bit-parallel, so all input vectors are evaluated by one integer operation | `testgen.py` | `--emit faults` |
| **Web playground** — edit MiniHDL in the browser, see diagnostics, a live clickable schematic, Verilog, optimizer report and all analyses | `server.py`, `web/index.html` | `python server.py` |

```bash
python mhdlc.py examples/adder.hdl --top FullAdder --emit boolean,timing,faults
python server.py                  # then use the page that opens (port 8000)
python server.py --port 9000 --no-browser
```

**Headline result.** Fault coverage is a second, independent measure of
optimizer quality. Redundant logic cannot be tested (no input vector can
expose a fault inside it), so an unoptimized netlist scores below 100%:

| Design | -O0 coverage | -O2 coverage |
|---|---|---|
| `Redundant` (optimize_demo) | 57.7% | 100% |
| `ALU4` | 92.0% | 100% |

The optimizer removes exactly the logic that no test could observe.

**Web playground API** (JSON, used by the page and testable with curl):
`GET /api/examples`, `POST /api/compile {source, top, olevel}`.
The server uses only the Python standard library and binds to 127.0.0.1.
