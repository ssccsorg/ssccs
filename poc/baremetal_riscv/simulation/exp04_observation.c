//! SSCCS on RISC-V: concept-04-observation
//!
//! Cross-validates the Observation concept Ω(Σ, F) = P:
//! - Field constraints filter which coordinates pass
//! - Passing coordinates get projected through a projector
//! - Rejected coordinates return REJECT sentinel (-1)
//!
//! This is the full pipeline: evaluate constraints → filter → project.

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

// Field: Range(axis0, 0..10)
static int field_allows_single(int64_t coord) {
    return ck_range(&coord, 0, 10);
}

// Identity projector
static int64_t project_identity(int64_t coord) {
    return coord;
}

// Sum projector (2D)
static int64_t project_sum2d(int64_t a, int64_t b) {
    return a + b;
}

// observe(coord): field.allows(coord) ? project(coord) : REJECT(-1)
static int64_t observe_single(int64_t coord) {
    if (field_allows_single(coord)) {
        return project_identity(coord);
    }
    return -1; // REJECT
}

// observe for 2D: range on both axes, sum projector
static int field_allows_2d(int64_t a, int64_t b) {
    if (!ck_range(&a, 0, 5)) return 0;
    if (!ck_range(&b, 0, 3)) return 0;
    return 1;
}

static int64_t observe_2d(int64_t a, int64_t b) {
    if (field_allows_2d(a, b)) {
        return project_sum2d(a, b);
    }
    return -1;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-04-observation ===\n");
    printf("Full pipeline: Field(constraints) → filter → Projector → result\n\n");

    // ── 1. Single-axis observation ──
    printf("1. Single-axis observation (Range 0..10, identity projector):\n");
    int64_t test_coords[] = {0, 5, 10, 11, -1, 3, 7};
    int64_t expected[] = {0, 5, 10, -1, -1, 3, 7};
    for (int i = 0; i < 7; i++) {
        int64_t result = observe_single(test_coords[i]);
        char buf[64];
        snprintf(buf, sizeof(buf), "  observe(%lld) == %lld",
                 (long long)test_coords[i], (long long)result);
        TEST(buf, result == expected[i]);
    }

    // ── 2. 2D observation ──
    printf("\n2. 2D observation (Range(0..5, 0..3), sum projector):\n");
    int64_t coords_a[] = {0, 5, 3, 6, 2, 1};
    int64_t coords_b[] = {0, 3, 2, 1, 4, 0};
    int64_t exp_2d[]  = {0, 8, 5, -1, -1, 1};
    const char *desc[] = {"in-range", "boundary", "both in-range",
                          "a out of range", "b out of range", "both in-range"};
    for (int i = 0; i < 6; i++) {
        int64_t result = observe_2d(coords_a[i], coords_b[i]);
        char buf[64];
        snprintf(buf, sizeof(buf), "  observe(%lld,%lld) [%s] == %lld",
                 (long long)coords_a[i], (long long)coords_b[i],
                 desc[i], (long long)result);
        TEST(buf, result == exp_2d[i]);
    }

    // ── 3. Observation with even constraint ──
    printf("\n3. Observation with even constraint (identity projector):\n");
    int64_t even_coords[] = {0, 1, 2, 3, 4, 5};
    for (int i = 0; i < 6; i++) {
        int64_t v = even_coords[i];
        int pass = ck_range(&v, 0, 10) && ck_even(&v);
        int64_t result = pass ? v : -1;
        int64_t expected_v = (v % 2 == 0 && v >= 0 && v <= 10) ? v : -1;
        char buf[64];
        snprintf(buf, sizeof(buf), "  observe(even+range %lld) == %lld",
                 (long long)even_coords[i], (long long)expected_v);
        TEST(buf, result == expected_v);
    }

    // ── 4. Same coord, different projectors ──
    printf("\n4. Same coordinate, different projectors:\n");
    int64_t v = 7;
    int in_range = ck_range(&v, 0, 10);
    if (in_range) {
        int64_t ident = project_identity(7);
        // parity via ck_even
        int64_t pv = 7;
        int even = ck_even(&pv);
        printf("   coord=7: identity=%lld, parity=%s\n",
               (long long)ident, even ? "even" : "odd");
        TEST("   Same coord, identity projector", ident == 7);
        TEST("   Same coord, parity projector", even == 0); // 7 is odd
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
