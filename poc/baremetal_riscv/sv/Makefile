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
TOP     := scenario_narrow_broad_tb
OBJDIR  := obj_dir
BIN     := $(OBJDIR)/V$(TOP)

# All SystemVerilog source files
SVSRCS  := $(SVDIR)/constraints/ck_even.sv \
           $(SVDIR)/constraints/ck_range_010.sv \
           $(SVDIR)/constraints/ck_range.sv \
           $(SVDIR)/observe.sv \
           $(SVDIR)/scenario_narrow_broad_tb.sv

.PHONY: all clean run check

all: $(BIN)

$(BIN): $(SVSRCS) $(SVDIR)/_golden_anchors.svh
	verilator --binary --timing --top-module $(TOP) \
		-Wno-fatal -Wno-WIDTH -Wno-UNUSED \
		-I$(SVDIR) \
		$(SVSRCS) \
		-CFLAGS "-O0" \
		--Mdir $(OBJDIR)

run: $(BIN)
	$(BIN)

check: $(BIN)
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

clean:
	rm -rf $(OBJDIR)
