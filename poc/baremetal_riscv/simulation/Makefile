# SSCCS Spike Runtime Validation Makefile
#
# Compiles and runs the RISC-V assembly constraint primitives under
# Spike + pk (proxy kernel) simulation.
#
# Requirements:
#   - riscv64-unknown-elf-gcc  (cross-compiler)
#   - spike                    (RISC-V ISA simulator)
#   - riscv-pk                  (proxy kernel, provides C runtime)

CC      := riscv64-unknown-elf-gcc
CFLAGS  := -Wall -Wextra -O0 -g

# Assembly source directory (relative to this Makefile)
ASMDIR  := ../../asm

# Source files
TEST_C  := spike_test.c
ASM_S   := $(ASMDIR)/observe_full.S

# Output
TARGET  := spike_test

# Path to proxy kernel (pk). If pk is installed to a custom location,
# override this variable:  make PK=/custom/path/to/pk
PK      := pk

.PHONY: all clean run check

all: $(TARGET)

$(TARGET): $(TEST_C) $(ASM_S)
	$(CC) $(CFLAGS) -o $@ $(TEST_C) $(ASM_S)

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
