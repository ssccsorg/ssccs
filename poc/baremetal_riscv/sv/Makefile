# SPDX-License-Identifier: CERN-OHL-P-2.0
# Copyright (C) 2026 Taeho Lee
#
# This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
# You may redistribute and modify this documentation and make products using
# it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
# documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
# INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
# PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
#
# SSCCS SystemVerilog Verification Makefile
#
# Compiles and runs the SystemVerilog observation engine testbench
# under Verilator simulation.
#
# Requirements:
#   - verilator (brew install verilator)
#
# The testbench asserts against golden anchors from asm/*.S files.
# Identical outputs across Rust, RISC-V asm, and SystemVerilog
# constitute the golden bridge.
#
# `generate` runs the host emitter, which writes modules into ../generated/ from a constraint program. `check`
# reaches them through generated-check and elaborate, so an emitted module is simulated and elaborated rather than
# merely written.

SVDIR   := .

# ── Scenario testbench ──

TOP     := scenario_narrow_broad_tb
OBJDIR  := obj_dir
BIN     := $(OBJDIR)/V$(TOP)

# ── The units ──
#
# One list, derived from the tree: every file under constraints/, projectors/ and composition/ is a unit, and so
# are observe and the XIF coprocessor. Testbenches live in tb/ and are never units. A new unit is a new file, and
# no list in this repository has to name it.

SV_UNITS := $(SVDIR)/observe.sv \
            $(SVDIR)/ssccs_xif_coprocessor.sv \
            $(wildcard $(SVDIR)/constraints/*.sv) \
            $(wildcard $(SVDIR)/projectors/*.sv) \
            $(wildcard $(SVDIR)/composition/*.sv)

# Modules the host emitter writes. Nothing under generated/ is committed; the elaboration gate compiles whatever is
# present, so the emitter has a consumer from its first commit.
GEN_DIR  := $(abspath $(SVDIR)/../generated)
GEN_MODULES := $(GEN_DIR)/ssccs_generated_narrow.sv $(GEN_DIR)/ssccs_generated_broad.sv
GEN_DECODERS := $(GEN_DIR)/ssccs_address_decode.sv $(GEN_DIR)/ssccs_line_decode.sv

SVSRCS  := $(SV_UNITS) $(SVDIR)/tb/$(TOP).sv

# ── The host emitter ──
#
# The binary writes both modules from one constraint pair, so a stamp records that they are current. A rule per
# output would run it twice for the same result.

# ── Composition testbench ──

COMPOSE_TOP     := composition_tb
COMPOSE_OBJDIR  := obj_dir_compose
COMPOSE_BIN     := $(COMPOSE_OBJDIR)/V$(COMPOSE_TOP)

COMPOSE_SRCS := $(SV_UNITS) $(SVDIR)/tb/$(COMPOSE_TOP).sv

.PHONY: all clean run check compose-check xif-check elaborate golden-anchor-check units generate generated-check generated-modules decode-check

WORKSPACE := $(abspath $(SVDIR)/../../standard)
EMITTED   := $(GEN_DIR)/.emitted

# The emitter's own sources and the spec it lowers: a change to either makes the written modules stale.
EMITTER_SRCS := $(wildcard $(WORKSPACE)/crates/hardware-mapping/src/*.rs) \
                $(wildcard $(WORKSPACE)/crates/hardware-mapping/src/bin/*.rs) \
                $(wildcard $(WORKSPACE)/crates/core/src/*.rs)

# The emitters report what they wrote, and a caller that only wants the module list must not receive that report as
# part of it. The rule writes the report to a file and `generate` shows it.
$(EMITTED): $(EMITTER_SRCS)
	@cd $(WORKSPACE) && { cargo run --release --quiet -p ssccs-hardware-mapping --bin emit-observation -- --out $(GEN_DIR) && cargo run --release --quiet -p ssccs-hardware-mapping --bin emit-decode -- --out $(GEN_DIR); } > $(GEN_DIR)/.emit.log 2>&1
	@touch $@

generate: $(EMITTED)
	@cat $(GEN_DIR)/.emit.log

# The board's flow asks for the emitted module paths the same way it asks for the units, so no caller repeats them.
generated-modules: $(EMITTED)
	@echo $(GEN_MODULES) $(GEN_DECODERS)

# The board's flow asks for this list rather than keeping one of its own. Absolute, so a caller in another
# directory can pass it to a tool that resolves paths against its own working directory.
units:
	@echo $(abspath $(SV_UNITS))

all: $(BIN)

# ── Scenario build / run / check ──

$(BIN): $(SVSRCS) $(SVDIR)/_golden_anchors.svh
	verilator --binary --timing --top-module $(TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) \
		$(SVSRCS) \
		-CFLAGS "-O0" \
		--Mdir $(OBJDIR)

run: $(BIN)
	$(BIN)

check: $(BIN) compose-check xif-check golden-anchor-check generated-check decode-check elaborate
	$(BIN); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo ""; \
		echo "SystemVerilog golden bridge: PASSED"; \
	else \
		echo ""; \
		echo "SystemVerilog golden bridge: FAILED (exit $$status)"; \
	fi; \
	exit $$status

# ── Golden anchor consistency ──

golden-anchor-check:
	python3 $(SVDIR)/check_golden_anchors.py

# ── Composition build / check ──

$(COMPOSE_BIN): $(COMPOSE_SRCS) $(SVDIR)/_golden_anchors.svh
	verilator --binary --timing --top-module $(COMPOSE_TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) -I$(SVDIR)/constraints -I$(SVDIR)/projectors -I$(SVDIR)/composition \
		$(COMPOSE_SRCS) \
		-CFLAGS "-O0" \
		--Mdir $(COMPOSE_OBJDIR)

compose-check: $(COMPOSE_BIN)
	$(COMPOSE_BIN); \
		status=$$?; \
		if [ $$status -eq 0 ]; then \
			echo ""; \
			echo "SystemVerilog composition: PASSED"; \
		else \
			echo ""; \
			echo "SystemVerilog composition: FAILED (exit $$status)"; \
		fi; \
		exit $$status

# ── XIF coprocessor ──

XIF_TOP     := xif_integration_tb
XIF_OBJDIR  := obj_dir_xif
XIF_BIN     := $(XIF_OBJDIR)/V$(XIF_TOP)

XIF_SRCS    := $(SV_UNITS) $(SVDIR)/tb/$(XIF_TOP).sv

$(XIF_BIN): $(XIF_SRCS) $(SVDIR)/_golden_anchors.svh $(SVDIR)/_xif_constants.svh
	verilator --binary --timing --assert --top-module $(XIF_TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) \
		$(XIF_SRCS) \
		-CFLAGS "-O0" \
		--Mdir $(XIF_OBJDIR)

# The coprocessor had no gate at all: its testbench was written and never built by check, which is how a module that
# passed signals into parameters stayed in the tree. The gate reads the run's own errors, because a testbench that
# prints them and exits zero is a report rather than a check.
xif-check: $(XIF_BIN)
	@echo "--- XIF coprocessor: the integration testbench ---"
	@./$(XIF_BIN) > $(XIF_OBJDIR)/run.log 2>&1 || { cat $(XIF_OBJDIR)/run.log; echo "XIF integration: FAILED"; exit 1; }
	@if grep -qE "%Error|Assertion failed" $(XIF_OBJDIR)/run.log; then \
		grep -E "%Error|Assertion failed" $(XIF_OBJDIR)/run.log; \
		echo "XIF integration: FAILED"; \
		exit 1; \
	fi
	@grep -E "All Golden Anchors Verified" $(XIF_OBJDIR)/run.log
	@echo "XIF integration: PASSED"

# ── Emitted modules ──

GEN_TOP     := generated_observation_tb
GEN_OBJDIR  := obj_dir_generated
GEN_BIN     := $(GEN_OBJDIR)/V$(GEN_TOP)

GEN_SRCS := $(SV_UNITS) $(GEN_MODULES) $(SVDIR)/tb/$(GEN_TOP).sv

# The modules themselves come from the stamp rather than from a file rule: what a rebuild depends on is that the
# emitter ran, and an output that was deleted without the stamp following it fails here rather than silently.
$(GEN_BIN): $(SV_UNITS) $(SVDIR)/tb/$(GEN_TOP).sv $(SVDIR)/_golden_anchors.svh $(EMITTED)
	verilator --binary --timing --assert --top-module $(GEN_TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) -I$(SVDIR)/constraints -I$(SVDIR)/projectors \
		$(GEN_SRCS) \
		-CFLAGS "-O0" \
		--Mdir $(GEN_OBJDIR)

# A module that elaborates still says nothing about what it computes, so the emitted pair answers the anchors in
# simulation. This is the only place the emitter's output meets a value rather than a grammar.
generated-check: $(GEN_BIN)
	@echo "--- emitted modules: the anchor table ---"
	@./$(GEN_BIN) > $(GEN_OBJDIR)/run.log 2>&1 || { cat $(GEN_OBJDIR)/run.log; echo "emitted modules: FAILED"; exit 1; }
	@if grep -qE "%Error|Assertion failed" $(GEN_OBJDIR)/run.log; then \
		grep -E "%Error|Assertion failed" $(GEN_OBJDIR)/run.log; \
		echo "emitted modules: FAILED"; \
		exit 1; \
	fi
	@grep -E "All Golden Anchors Verified" $(GEN_OBJDIR)/run.log
	@echo "emitted modules: PASSED"

# ── Emitted address decode ──
#
# The decoder is arithmetic the emitter wrote over a Scheme's extents. The tables it is compared against come from
# the Scheme's segments, so the sweep is two derivations of one space rather than one derivation twice.

DECODE_TOP    := address_decode_tb
DECODE_OBJDIR := obj_dir_decode
DECODE_BIN    := $(DECODE_OBJDIR)/V$(DECODE_TOP)
DECODE_TOTAL  := 12
DECODE_WIDTH  := 4

# The module itself comes from the stamp, like the Field half's modules: a prerequisite on a generated file with no
# rule of its own fails on a tree where nothing has been emitted yet.
$(DECODE_BIN): $(SVDIR)/tb/$(DECODE_TOP).sv $(EMITTED)
	verilator --binary --timing --assert --top-module $(DECODE_TOP) \
		-GTOTAL=$(DECODE_TOTAL) -GWIDTH=$(DECODE_WIDTH) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		$(SVDIR)/tb/$(DECODE_TOP).sv $(GEN_DIR)/ssccs_address_decode.sv \
		-CFLAGS "-O0" --Mdir $(DECODE_OBJDIR)

decode-check: $(DECODE_BIN)
	@echo "--- emitted decode: the Scheme's addresses ---"
	@./$(DECODE_BIN) +coord0=$(GEN_DIR)/address_coord0.hex +coord1=$(GEN_DIR)/address_coord1.hex \
		> $(DECODE_OBJDIR)/run.log 2>&1 \
		|| { cat $(DECODE_OBJDIR)/run.log; echo "emitted decode: FAILED"; exit 1; }
	@if grep -qE "%Error|Assertion failed" $(DECODE_OBJDIR)/run.log; then \
		grep -E "%Error|Assertion failed" $(DECODE_OBJDIR)/run.log; \
		echo "emitted decode: FAILED"; \
		exit 1; \
	fi
	@grep -E "All Addresses Verified" $(DECODE_OBJDIR)/run.log
	@echo "emitted decode: PASSED"

# ── Elaboration ──

# read_verilog evaluates every parameter override, so a module that passes a signal into a parameter fails here
# rather than at the first synthesis of a design that happens to instantiate it.
# The units and whatever the emitter has written so far. A generated module that does not elaborate fails here,
# which is the first place a bad emission can be caught. The glob is expanded by the shell, after the emitter has
# run, because make expands its own variables before any recipe does.
elaborate: $(EMITTED)
	@if command -v yosys >/dev/null 2>&1; then \
		echo "--- yosys: every module elaborates ---"; \
		generated=$$(ls $(GEN_DIR)/*.sv 2>/dev/null | tr '\n' ' '); \
		yosys -q -p "read_verilog -sv -I$(SVDIR) $(SV_UNITS) $$generated" && echo "  all modules elaborate"; \
	else \
		echo "  skipped (yosys is not installed)"; \
	fi

clean:
	rm -rf $(OBJDIR) $(COMPOSE_OBJDIR) $(XIF_OBJDIR) $(GEN_OBJDIR) $(DECODE_OBJDIR)
