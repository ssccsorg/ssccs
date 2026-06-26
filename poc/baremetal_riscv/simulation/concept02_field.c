//! SSCCS on RISC-V: concept-02-field
//!
//! Cross-validates the Field concept:
//! - Multiple constraints: Range + Even
//! - RISC-V asm functions reused: ck_range, ck_even (from observe_full.S)
//!
//! Field: Range(axis0, 0..10) + Range(axis1, 0..5) + Even(axis0)
//! Projector: identity (returns axis0 value)

#include <stdio.h>
#include <stdint.h>

static int total_passed = 0;
static int total_failed = 0;

// Assembly functions from observe_full.S
extern int ck_even(int64_t *val);
extern int ck_range(int64_t *coord, int64_t min, int64_t max);

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

// Field constraints: Range(axis0, 0, 10) + Range(axis1, 0, 5) + Even(axis0)
// axis0 = values[0], axis1 = values[1], axis2 = values[2] (unconstrained)
static int field_allows(int64_t *values) {
    int64_t axis0 = values[0];
    int64_t axis1 = values[1];
    // Range(0, 10) on axis0  → ck_range(&axis0, 0, 10)
    // Range(0, 5)  on axis1  → ck_range(&axis1, 0, 5)
    // Even on axis0          → ck_even(&axis0)
    if (!ck_range(&axis0, 0, 10)) return 0;
    if (!ck_range(&axis1, 0, 5))  return 0;
    if (!ck_even(&axis0))         return 0;
    return 1;
}

// Identity projector on axis0
static int64_t project_identity_axis0(int64_t *values) {
    return values[0];
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-02-field ===\n");
    printf("Constraints: Range(axis0,0..10) + Range(axis1,0..5) + Even(axis0)\n");
    printf("Projector: identity(axis0)\n\n");

    // Test cases matching Rust concept-02-field
    //     [axis0, axis1, axis2] → expected (pass? projection)
    // (1) [4, 3, 100] → pass, projection=4  (even, within both ranges)
    // (2) [15, 3, 0]  → fail (axis0 out of range)
    // (3) [3, 2, 0]   → fail (axis0 odd)
    // (4) [0, 7, 0]   → fail (axis1 out of range 0..5)
    // (5) [6, 0, 0]   → pass, projection=6  (even, within ranges)
    // (6) [10, 5, 0]  → pass, projection=10 (edge case: both at max)

    int64_t test_cases[][3] = {
        {4, 3, 100},   // should pass
        {15, 3, 0},    // should fail: axis0 out of range
        {3, 2, 0},     // should fail: axis0 odd
        {0, 7, 0},     // should fail: axis1 out of range
        {6, 0, 0},     // should pass
        {10, 5, 0},    // should pass
        {2, 4, 99},    // should pass
        {1, 0, 0},     // should fail: axis0 odd
        {8, 2, 0},     // should pass
        {-1, 0, 0},    // should fail: negative
    };
    int num_cases = sizeof(test_cases) / sizeof(test_cases[0]);

    struct { int pass; int64_t proj; } expected[] = {
        {1, 4}, {0, 0}, {0, 0}, {0, 0}, {1, 6},
        {1, 10}, {1, 2}, {0, 0}, {1, 8}, {0, 0},
    };
    const char *desc[] = {
        "[4,3,100] even+in-range",
        "[15,3,0] axis0 out of range",
        "[3,2,0] axis0 odd",
        "[0,7,0] axis1 out of range",
        "[6,0,0] even+in-range",
        "[10,5,0] boundary max",
        "[2,4,99] even+in-range",
        "[1,0,0] axis0 odd",
        "[8,2,0] even+in-range",
        "[-1,0,0] negative",
    };

    for (int i = 0; i < num_cases; i++) {
        int pass = field_allows(test_cases[i]);
        int64_t proj = pass ? project_identity_axis0(test_cases[i]) : -1;
        int ok = (pass == expected[i].pass) && (!pass || proj == expected[i].proj);
        char buf[128];
        snprintf(buf, sizeof(buf), "%s → %s (proj=%lld)", desc[i],
                 pass ? "PASS" : "FAIL", (long long)proj);
        TEST(buf, ok);
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
