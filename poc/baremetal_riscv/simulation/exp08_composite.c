//! SSCCS on RISC-V: concept-08-composite
//!
//! Cross-validates Composite and Transformed Scheme concepts:
//! - Field union (∪): coord passes if any sub-field allows it
//! - Field intersection (∩): coord passes only if all sub-fields allow it
//! - Translation: coordinate transformation
//! - Multiple fields combined via composite rules

#include <stdio.h>
#include <stdint.h>

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

// Assembly constraint primitives
extern int ck_even(int64_t *val);
extern int ck_range(int64_t *coord, int64_t min, int64_t max);

// ── Field definitions ──
// Field A: Range(0..10) even
static int field_a_allows(int64_t coord) {
    return ck_range(&coord, 0, 10) && ck_even(&coord);
}

// Field B: Range(5..15)
static int field_b_allows(int64_t coord) {
    return ck_range(&coord, 5, 15);
}

// ── Composite operations ──

// Union (∪): coord passes if either field allows it
static int field_union_allows(int64_t coord) {
    return field_a_allows(coord) || field_b_allows(coord);
}

// Intersection (∩): coord passes only if both fields allow it
static int field_intersection_allows(int64_t coord) {
    return field_a_allows(coord) && field_b_allows(coord);
}

// ── Identity projector ──
static int64_t project_identity(int64_t coord) { return coord; }

// Translation: offset = coord + dx
static int64_t translate(int64_t coord, int64_t dx) { return coord + dx; }

int main(void) {
    printf("=== SSCCS on RISC-V: concept-08-composite ===\n");
    printf("Field composition: Union(∪), Intersection(∩), Translation\n\n");

    // Field A: Range(0..10) even → {0, 2, 4, 6, 8, 10}
    // Field B: Range(5..15) → {5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}

    // ── 1. Individual fields ──
    printf("1. Individual fields:\n");
    int64_t test_vals[] = {0, 2, 4, 6, 8, 10, 5, 7, 9, 11, 13, 15, 3, 12};
    for (int i = 0; i < 14; i++) {
        int64_t v = test_vals[i];
        int a = field_a_allows(v);
        int b = field_b_allows(v);
        char buf[80];
        snprintf(buf, sizeof(buf), "  coord=%lld: A=%s, B=%s", (long long)v,
                 a ? "PASS" : "FAIL", b ? "PASS" : "FAIL");
        // Expected: A passes even [0,10], B passes [5,15]
        int expected_a = (v % 2 == 0 && v >= 0 && v <= 10);
        int expected_b = (v >= 5 && v <= 15);
        TEST(buf, a == expected_a && b == expected_b);
    }

    // ── 2. Union (∪) ──
    printf("\n2. Field Union (A ∪ B):\n");
    // Union passes if coord is in A OR B
    // Expected passes: {0,2,4,6,8,10} from A + {5,7,9,11,13,15} from B
    //                 = {0,2,4,5,6,7,8,9,10,11,13,15}
    // 12 passes B only, 3 passes neither
    for (int i = 0; i < 14; i++) {
        int64_t v = test_vals[i];
        int result = field_union_allows(v);
        int expected = field_a_allows(v) || field_b_allows(v);
        char buf[80];
        snprintf(buf, sizeof(buf), "  Union(%lld) %s", (long long)v, result ? "PASS" : "FAIL");
        TEST(buf, result == expected);
    }

    // ── 3. Intersection (∩) ──
    printf("\n3. Field Intersection (A ∩ B):\n");
    // Intersection passes only if coord is in A AND B
    // A∩B = even numbers in [5..10] = {6, 8, 10}
    for (int i = 0; i < 14; i++) {
        int64_t v = test_vals[i];
        int result = field_intersection_allows(v);
        int expected = field_a_allows(v) && field_b_allows(v);
        char buf[80];
        snprintf(buf, sizeof(buf), "  Intersection(%lld) %s", (long long)v, result ? "PASS" : "FAIL");
        TEST(buf, result == expected);
    }

    // Verify exact set
    int intersection_count = 0;
    int64_t intersection_vals[14];
    for (int i = 0; i < 14; i++) {
        if (field_intersection_allows(test_vals[i])) {
            intersection_vals[intersection_count++] = test_vals[i];
        }
    }
    TEST("  Intersection count == 3 (6,8,10)", intersection_count == 3);
    TEST("  Intersection contains 6", intersection_vals[0] == 6 ||
         intersection_vals[1] == 6 || intersection_vals[2] == 6);
    TEST("  Intersection contains 8", intersection_vals[0] == 8 ||
         intersection_vals[1] == 8 || intersection_vals[2] == 8);
    TEST("  Intersection contains 10", intersection_vals[0] == 10 ||
          intersection_vals[1] == 10 || intersection_vals[2] == 10);

    // ── 4. Translation ──
    printf("\n4. Coordinate transformation (Translation):\n");
    // Translate(coord, dx) = coord + dx
    // Original coord 0 with dx=5 → 5
    TEST("  translate(0, 5) == 5", translate(0, 5) == 5);
    TEST("  translate(5, -3) == 2", translate(5, -3) == 2);
    TEST("  translate(-2, 2) == 0", translate(-2, 2) == 0);

    // Transformed Field: original coord 0 (even, in range) after translate -5
    // translates to -5 which is NOT in Field A (range 0..10)
    int64_t original = 0;
    int64_t translated = translate(original, -5);
    int in_field_a = field_a_allows(translated);
    char buf[80];
    snprintf(buf, sizeof(buf), "  translate(0, -5)=%lld in Field A: %s",
             (long long)translated, in_field_a ? "PASS" : "FAIL");
    TEST(buf, translated == -5 && !in_field_a);

    // ── 5. Composite identity projector ──
    printf("\n5. Composite observation (Union + projector):\n");
    int64_t union_pass_vals[] = {0, 6, 10, 12};
    for (int i = 0; i < 4; i++) {
        int64_t v = union_pass_vals[i];
        int64_t proj = field_union_allows(v) ? project_identity(v) : -1;
        char buf[80];
        snprintf(buf, sizeof(buf), "  Union observe(%lld) == %lld", (long long)v, (long long)proj);
        TEST(buf, field_union_allows(v) == (v == 0 || v == 6 || v == 10 || v == 12));
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
