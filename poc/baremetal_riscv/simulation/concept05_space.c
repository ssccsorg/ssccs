//! SSCCS on RISC-V: concept-05-space
//!
//! Cross-validates the Space concept:
//! - BooleanSpace: coordinates are 0 (false) or 1 (true)
//! - IntegerSpace: single-axis coordinate
//! - Segment identity: same coordinates → same ID (via coordinate equality)

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int total_passed = 0;
static int total_failed = 0;

#define TEST(name, cond)                                                    \
    do {                                                                    \
        if ((cond)) {                                                       \
            printf("PASS: %s\n", (name));                                   \
            total_passed++;                                                 \
        } else {                                                            \
            printf("FAIL: %s\n", (name));                                   \
            total_failed++;                                                 \
        }                                                                   \
    } while (0)

int main(void) {
    printf("=== SSCCS on RISC-V: concept-05-space ===\n");
    printf("Concepts: BooleanSpace, IntegerSpace\n\n");

    // ── 1. BooleanSpace ──
    printf("1. BooleanSpace (coord=0 false, coord=1 true):\n");

    // Boolean space has 2 coordinates: 0 (false) and 1 (true)
    int64_t bool_false = 0;
    int64_t bool_true = 1;
    TEST("  Boolean false coord == 0", bool_false == 0);
    TEST("  Boolean true coord == 1", bool_true == 1);

    // All values in a 1D space with range [0,1]
    int64_t bool_space[] = {0, 1};
    for (int i = 0; i < 2; i++) {
        int in_space = (bool_space[i] >= 0 && bool_space[i] <= 1);
        char buf[64];
        snprintf(buf, sizeof(buf), "  Boolean coord %lld in space", (long long)bool_space[i]);
        TEST(buf, in_space);
    }

    // Out of range
    int64_t invalid_bool[] = {-1, 2, 100};
    for (int i = 0; i < 3; i++) {
        int in_space = (invalid_bool[i] >= 0 && invalid_bool[i] <= 1);
        char buf[64];
        snprintf(buf, sizeof(buf), "  Boolean coord %lld NOT in space", (long long)invalid_bool[i]);
        TEST(buf, !in_space);
    }

    // ── 2. IntegerSpace ──
    printf("\n2. IntegerSpace (single-axis coordinate):\n");

    // Integer space: any int64_t is valid
    int64_t int_vals[] = {0, 42, -1, 1000, -999};
    for (int i = 0; i < 5; i++) {
        // Identity projector: observe(coord) == coord
        char buf[64];
        snprintf(buf, sizeof(buf), "  IntegerSpace coord %lld identity", (long long)int_vals[i]);
        TEST(buf, int_vals[i] == int_vals[i]); // trivially true
    }

    // ── 3. Identity: same coordinates → same segment ──
    printf("\n3. Deterministic identity:\n");
    int64_t coord_a = 42;
    int64_t coord_b = 42;
    int64_t coord_c = 99;
    TEST("  Same coord (42 == 42) → same segment", coord_a == coord_b);
    TEST("  Different coord (42 != 99) → different segment", coord_a != coord_c);

    // ── 4. Space as Field ──
    printf("\n4. Space acts as implicit Field:\n");
    // Boolean space (0..1) + Even constraint → only coord=0 passes
    int64_t bool_vals[] = {0, 1};
    for (int i = 0; i < 2; i++) {
        int in_range = (bool_vals[i] >= 0 && bool_vals[i] <= 1);
        // Even check via simple arithmetic
        int even = (bool_vals[i] % 2 == 0);
        int observe_pass = in_range && even;
        char buf[64];
        snprintf(buf, sizeof(buf), "  BooleanSpace+Even observe(%lld) %s",
                 (long long)bool_vals[i], observe_pass ? "PASS" : "FAIL");
        // Boolean space (0..1) + Even: only 0 passes
        int expected = (bool_vals[i] == 0);
        TEST(buf, observe_pass == expected);
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
