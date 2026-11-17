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

SVDIR   := .

# ── Scenario testbench ──

TOP     := scenario_narrow_broad_tb
OBJDIR  := obj_dir
BIN     := $(OBJDIR)/V$(TOP)

SVSRCS  := $(SVDIR)/constraints/ck_even.sv \
           $(SVDIR)/constraints/ck_range.sv \
           $(SVDIR)/constraints/ck_range_010.sv \
           $(SVDIR)/observe.sv \
           $(SVDIR)/scenario_narrow_broad_tb.sv

# ── Composition testbench ──

COMPOSE_TOP     := composition_tb
COMPOSE_OBJDIR  := obj_dir_compose
COMPOSE_BIN     := $(COMPOSE_OBJDIR)/V$(COMPOSE_TOP)

COMPOSE_SRCS := $(SVDIR)/composition/compose_union.sv \
               $(SVDIR)/composition/compose_intersect.sv \
               $(SVDIR)/composition/compose_product_2d.sv \
               $(SVDIR)/composition/compose_pipeline.sv \
               $(SVDIR)/projectors/proj_mul.sv \
               $(SVDIR)/projectors/proj_div.sv \
               $(SVDIR)/composition/composition_tb.sv

.PHONY: all clean run check compose-check xif-check elaborate

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

check: $(BIN) compose-check xif-check golden-anchor-check elaborate
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

XIF_SRCS    := $(SVDIR)/ssccs_xif_coprocessor.sv \
               $(SVDIR)/constraints/ck_even.sv \
               $(SVDIR)/constraints/ck_range.sv \
               $(SVDIR)/constraints/ck_range_010.sv \
               $(SVDIR)/constraints/ck_eq.sv \
               $(SVDIR)/constraints/ck_gt.sv \
               $(SVDIR)/projectors/proj_identity.sv \
               $(SVDIR)/projectors/proj_negate.sv \
               $(SVDIR)/projectors/proj_parity.sv \
               $(SVDIR)/projectors/proj_sum2d.sv \
               $(SVDIR)/projectors/proj_sum3d.sv \
               $(SVDIR)/xif_integration_tb.sv

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

# ── Elaboration ──

# read_verilog evaluates every parameter override, so a module that passes a signal into a parameter fails here
# rather than at the first synthesis of a design that happens to instantiate it.
ELAB_SRCS   := $(filter-out %_tb.sv,$(wildcard $(SVDIR)/*.sv $(SVDIR)/constraints/*.sv \
               $(SVDIR)/projectors/*.sv $(SVDIR)/composition/*.sv))

elaborate:
	@if command -v yosys >/dev/null 2>&1; then \
		echo "--- yosys: every module elaborates ---"; \
		yosys -q -p "read_verilog -sv -I$(SVDIR) $(ELAB_SRCS)" && echo "  all modules elaborate"; \
	else \
		echo "  skipped (yosys is not installed)"; \
	fi

clean:
	rm -rf $(OBJDIR) $(COMPOSE_OBJDIR) $(XIF_OBJDIR)
