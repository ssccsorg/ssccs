//! SSCCS on RISC-V: concept-03-projector
//!
//! Cross-validates the Projector concept:
//! - IntegerProjector: identity (returns coordinate value)
//! - ParityProjector: even/odd classification
//! - ArithmeticProjector: sum of all axes
//!
//! Demonstrates: same coordinates → different meanings depending on projector.

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int total_passed = 0;
static int total_failed = 0;

// Assembly functions from observe_full.S
extern int ck_even(int64_t *val);

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

// IntegerProjector: returns coordinate value at given axis
static int64_t project_integer(int64_t *values, int axis) {
    return values[axis];
}

// ParityProjector: returns 0 for even, 1 for odd (of axis 0)
static int project_parity(int64_t *values) {
    int64_t v = values[0];
    int result = ck_even(&v);
    return result ? 0 : 1; // 0=even, 1=odd
}

// ArithmeticProjector: sum of all axes
static int64_t project_sum(int64_t *values, int num_axes) {
    int64_t s = 0;
    for (int i = 0; i < num_axes; i++) s += values[i];
    return s;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-03-projector ===\n");
    printf("Projectors: Integer(identity), Parity(even/odd), Arithmetic(sum)\n\n");

    // Test coordinates
    int64_t test_coords[] = {7, 3, 1, 0, 2, 9, -4, 100};
    int num = sizeof(test_coords) / sizeof(test_coords[0]);

    printf("1. IntegerProjector (identity) on axis 0:\n");
    printf("   Same as concept-01-segment: observe(coord) == coord\n");
    for (int i = 0; i < num; i++) {
        int64_t result = project_integer(&test_coords[i], 0);
        char buf[64];
        snprintf(buf, sizeof(buf), "  Integer(%lld) == %lld", (long long)test_coords[i], (long long)result);
        TEST(buf, result == test_coords[i]);
    }

    printf("\n2. ParityProjector on axis 0:\n");
    for (int i = 0; i < num; i++) {
        int parity = project_parity(&test_coords[i]);
        int expected = (test_coords[i] % 2 == 0) ? 0 : 1;
        char buf[64];
        snprintf(buf, sizeof(buf), "  Parity(%lld) == %s",
                 (long long)test_coords[i], parity == 0 ? "even" : "odd");
        TEST(buf, parity == expected);
    }

    printf("\n3. ArithmeticProjector (sum):\n");
    // Single-value: sum = value itself
    for (int i = 0; i < num; i++) {
        int64_t result = project_sum(&test_coords[i], 1);
        char buf[64];
        snprintf(buf, sizeof(buf), "  Sum(%lld) == %lld", (long long)test_coords[i], (long long)result);
        TEST(buf, result == test_coords[i]);
    }

    // Multi-value: sum of all axes
    printf("\n4. ArithmeticProjector on multi-axis:\n");
    int64_t multi[][3] = {{2, 1, 0}, {1, 2, 3}, {5, 5, 5}, {0, 0, 0}};
    int64_t expected_sums[] = {3, 6, 15, 0};
    for (int i = 0; i < 4; i++) {
        int64_t result = project_sum(multi[i], 3);
        char buf[64];
        snprintf(buf, sizeof(buf), "  Sum(%lld,%lld,%lld) == %lld (expected %lld)",
                 (long long)multi[i][0], (long long)multi[i][1], (long long)multi[i][2],
                 (long long)result, (long long)expected_sums[i]);
        TEST(buf, result == expected_sums[i]);
    }

    printf("5. Same coordinates → different meanings:\n");
    int64_t val_single = 7;
    int64_t val_multi[3] = {7, 0, 0};
    int64_t int_proj = project_integer(&val_single, 0);
    int par_proj = project_parity(val_multi);
    int64_t sum_proj = project_sum(val_multi, 3);
    printf("   coordinate=7: Integer=%lld, Parity=%s, Sum=%lld\n",
           (long long)int_proj, par_proj == 0 ? "even" : "odd", (long long)sum_proj);
    TEST("   Same coord, different interpretations",
         int_proj == 7 && par_proj == 1 && sum_proj == 7);

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
