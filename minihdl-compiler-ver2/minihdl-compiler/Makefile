PY      ?= python3
MHDLC   := $(PY) mhdlc.py
OUT     := build

.PHONY: web analyze all demo test adder alu datapath optimize errors svg clean help

help:
	@echo "targets:"
	@echo "  make web       start the web playground (http://127.0.0.1:8000)"
	@echo "  make analyze   Boolean minimisation + timing + fault coverage"
	@echo "  make test      run the 32-test regression suite"
	@echo "  make demo      compile every example with full output"
	@echo "  make adder     FullAdder + RippleCarry4"
	@echo "  make alu       the 4-bit ALU, all artefacts"
	@echo "  make optimize  -O0 vs -O2 comparison"
	@echo "  make errors    show the diagnostic engine"
	@echo "  make svg       render schematics with Graphviz"
	@echo "  make clean     remove $(OUT)/"

web:
	$(PY) server.py

analyze:
	$(MHDLC) examples/adder.hdl --top FullAdder --emit boolean,timing,faults
	$(MHDLC) examples/optimize_demo.hdl --top Redundant -O0 --emit faults
	$(MHDLC) examples/optimize_demo.hdl --top Redundant -O2 --emit faults

test:
	$(PY) tests/test_suite.py

demo: adder alu datapath optimize

adder:
	$(MHDLC) examples/adder.hdl --top FullAdder    --emit all -O2 --verify
	$(MHDLC) examples/adder.hdl --top RippleCarry4 --emit stats,verilog -O2 --verify

alu:
	$(MHDLC) examples/alu.hdl --top ALU4 --emit all -O2 --verify

datapath:
	$(MHDLC) examples/datapath.hdl --top Datapath       --emit stats,verilog -O2 --verify
	$(MHDLC) examples/datapath.hdl --top PriorityEncoder --emit truth,stats  -O2 --verify

optimize:
	@echo "=== -O0 ==="
	$(MHDLC) examples/optimize_demo.hdl --top Redundant -O0 --emit ir,stats
	@echo "=== -O2 ==="
	$(MHDLC) examples/optimize_demo.hdl --top Redundant -O2 --emit opt,stats,truth --verify

errors:
	-$(MHDLC) examples/errors.hdl

svg: 
	$(MHDLC) examples/adder.hdl --top FullAdder --emit dot -O2
	$(MHDLC) examples/alu.hdl   --top ALU4      --emit dot -O2
	dot -Tsvg $(OUT)/FullAdder.dot -o $(OUT)/FullAdder.svg
	dot -Tsvg $(OUT)/ALU4.dot      -o $(OUT)/ALU4.svg
	@echo "wrote $(OUT)/FullAdder.svg and $(OUT)/ALU4.svg"

clean:
	rm -rf $(OUT) **/__pycache__ minihdl/__pycache__ tests/__pycache__
