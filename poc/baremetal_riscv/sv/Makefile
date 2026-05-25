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
               $(SVDIR)/composition/composition_tb.sv

.PHONY: all clean run check compose-check

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

check: $(BIN) compose-check
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

# ── Composition build / check ──

$(COMPOSE_BIN): $(COMPOSE_SRCS) $(SVDIR)/_golden_anchors.svh
	verilator --binary --timing --top-module $(COMPOSE_TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) \
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

clean:
	rm -rf $(OBJDIR) $(COMPOSE_OBJDIR)
