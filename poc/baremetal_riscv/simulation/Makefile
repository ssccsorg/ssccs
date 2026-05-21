# SSCCS Spike Runtime Validation Makefile
#
# Compiles and runs the RISC-V assembly constraint primitives under
# Spike + pk (proxy kernel) simulation.
#
# Requirements:
#   - riscv64-unknown-elf-gcc or riscv64-linux-gnu-gcc  (cross-compiler)
#   - spike                    (RISC-V ISA simulator)
#   - riscv-pk                  (proxy kernel, provides C runtime)
#
# The PK variable must be a path that spike can open as a file.
# Set PK as an environment variable (e.g. PK=/usr/local/.../bin/pk)
# or let it default to bare "pk".

CC      := riscv64-unknown-elf-gcc
CFLAGS  := -static -Wall -Wextra -O0 -g

# Assembly source directory (relative to this Makefile)
ASMDIR  := ../asm

# Source files
TEST_C  := spike_test.c
STUBS_C := stubs.c
ASM_S   := $(ASMDIR)/observe_full.S

# Output
TARGET  := spike_test

# Path to proxy kernel (pk). Prefer environment variable, fall back
# to bare name for CI / local development.
PK      ?= pk

.PHONY: all clean run check

all: $(TARGET)

$(TARGET): $(TEST_C) $(STUBS_C) $(ASM_S)
	$(CC) $(CFLAGS) -o $@ $(TEST_C) $(STUBS_C) $(ASM_S)

# Run under Spike with proxy kernel
run: $(TARGET)
	spike $(PK) $(TARGET)

# Run and check exit code (0 = all tests passed)
check: $(TARGET)
	spike $(PK) $(TARGET); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo "All tests passed."; \
	else \
		echo "Some tests failed (exit code: $$status)."; \
	fi; \
	exit $$status

clean:
	rm -f $(TARGET)
