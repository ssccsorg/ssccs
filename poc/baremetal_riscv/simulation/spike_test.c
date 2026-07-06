/*
 * SSCCS Spike Runtime Validation
 *
 * Standalone C test that calls RISC-V assembly constraint primitives from
 * observe_full.S and validates their outputs. Runs under Spike + pk.
 *
 * Whitepaper 2.3.2 alignment: branchless constraint primitives are
 * verified against known inputs to confirm correct RV64 execution.
 */

#include <stdio.h>

/*
 * Assembly function declarations.
 *
 * These functions take the i64 value via pointer (a0 contains the address)
 * because the prologue uses ld t0, 0(a0) to load the 64-bit operand.
 * See poc/baremetal_riscv/asm/observe_full.S for the implementation.
 */
extern int ck_even(long long *val);
extern int ck_range_0_10(long long *coord);
extern int ck_range(long long *coord, long long min, long long max);
extern int ck_eq_val(long long *val, long long target);
extern int ck_gt(long long *coord, long long target);

/* Operator-level projectors (new in compose-field) */
extern long long proj_mul(long long a, long long b);
extern long long proj_div(long long a, long long b);

/* Test harness helpers */
static int total_passed = 0;
static int total_failed = 0;

#define TEST(name, cond, expected, actual)                              \
    do {                                                                \
        if ((cond)) {                                                   \
            printf("PASS: %s\n", (name));                              \
            total_passed++;                                             \
        } else {                                                        \
            printf("FAIL: %s (expected %d, got %d)\n",                \
                   (name), (expected), (actual));                       \
            total_failed++;                                             \
        }                                                               \
    } while (0)

int main(void)
{
    long long val;
    int result;

    /*
     * ck_even: returns 1 if the value is even.
     * Even values: ..., -4, -2, 0, 2, 4, ...
     */
    val = 0;
    result = ck_even(&val);
    TEST("ck_even(0)", result == 1, 1, result);

    val = 1;
    result = ck_even(&val);
    TEST("ck_even(1)", result == 0, 0, result);

    val = 42;
    result = ck_even(&val);
    TEST("ck_even(42)", result == 1, 1, result);

    val = 999;
    result = ck_even(&val);
    TEST("ck_even(999)", result == 0, 0, result);

    val = -2;
    result = ck_even(&val);
    TEST("ck_even(-2)", result == 1, 1, result);

    val = -3;
    result = ck_even(&val);
    TEST("ck_even(-3)", result == 0, 0, result);

    /*
     * ck_range_0_10: returns 1 if coord in [0, 10] inclusive.
     */
    val = 0;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(0)", result == 1, 1, result);

    val = 5;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(5)", result == 1, 1, result);

    val = 10;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(10)", result == 1, 1, result);

    val = 11;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(11)", result == 0, 0, result);

    val = -1;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(-1)", result == 0, 0, result);

    val = 255;
    result = ck_range_0_10(&val);
    TEST("ck_range_0_10(255)", result == 0, 0, result);

    /*
     * ck_range: returns 1 if coord in [min, max] inclusive.
     * Parameters: coord (pointer), min, max.
     */
    val = 5;
    result = ck_range(&val, 0, 10);
    TEST("ck_range(5, 0, 10)", result == 1, 1, result);

    val = 0;
    result = ck_range(&val, 0, 10);
    TEST("ck_range(0, 0, 10)", result == 1, 1, result);

    val = 10;
    result = ck_range(&val, 0, 10);
    TEST("ck_range(10, 0, 10)", result == 1, 1, result);

    val = -1;
    result = ck_range(&val, 0, 10);
    TEST("ck_range(-1, 0, 10)", result == 0, 0, result);

    val = 11;
    result = ck_range(&val, 0, 10);
    TEST("ck_range(11, 0, 10)", result == 0, 0, result);

    val = 3;
    result = ck_range(&val, 5, 10);
    TEST("ck_range(3, 5, 10)", result == 0, 0, result);

    val = 7;
    result = ck_range(&val, 5, 10);
    TEST("ck_range(7, 5, 10)", result == 1, 1, result);

    val = 100;
    result = ck_range(&val, -50, 50);
    TEST("ck_range(100, -50, 50)", result == 0, 0, result);

    val = 0;
    result = ck_range(&val, -50, 50);
    TEST("ck_range(0, -50, 50)", result == 1, 1, result);

    /*
     * ck_eq_val: returns 1 if val == target.
     */
    val = 42;
    result = ck_eq_val(&val, 42);
    TEST("ck_eq_val(42, 42)", result == 1, 1, result);

    val = 42;
    result = ck_eq_val(&val, 43);
    TEST("ck_eq_val(42, 43)", result == 0, 0, result);

    val = -1;
    result = ck_eq_val(&val, -1);
    TEST("ck_eq_val(-1, -1)", result == 1, 1, result);

    val = 0;
    result = ck_eq_val(&val, 0);
    TEST("ck_eq_val(0, 0)", result == 1, 1, result);

    /*
     * ck_gt: returns 1 if coord > target.
     */
    val = 10;
    result = ck_gt(&val, 5);
    TEST("ck_gt(10, 5)", result == 1, 1, result);

    val = 5;
    result = ck_gt(&val, 10);
    TEST("ck_gt(5, 10)", result == 0, 0, result);

    val = 5;
    result = ck_gt(&val, 5);
    TEST("ck_gt(5, 5)", result == 0, 0, result);

    val = -1;
    result = ck_gt(&val, -5);
    TEST("ck_gt(-1, -5)", result == 1, 1, result);

    val = -10;
    result = ck_gt(&val, -5);
    TEST("ck_gt(-10, -5)", result == 0, 0, result);

    /* Summary */

    /*
     * proj_mul(a, b): returns a * b.
     */
    printf("\n-- proj_mul / proj_div --\n");

    result = proj_mul(7, 6);
    TEST("proj_mul(7,6)", result == 42, 42, result);

    result = proj_mul(-3, 4);
    TEST("proj_mul(-3,4)", result == -12, -12, result);

    result = proj_mul(0, 999);
    TEST("proj_mul(0,999)", result == 0, 0, result);

    /*
     * proj_div(a, b): returns a / b (0 if b == 0).
     */
    result = proj_div(42, 6);
    TEST("proj_div(42,6)", result == 7, 7, result);

    result = proj_div(100, 3);
    TEST("proj_div(100,3)", result == 33, 33, result);

    result = proj_div(42, 0);
    TEST("proj_div(42,0)", result == 0, 0, result);

    printf("\n=== SUMMARY ===\n");
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);
    printf("Total:  %d\n", total_passed + total_failed);

    return total_failed > 0 ? 1 : 0;
}
