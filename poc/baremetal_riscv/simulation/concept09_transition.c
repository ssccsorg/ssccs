//! SSCCS on RISC-V: concept-09-transition
//!
//! Cross-validates Transition Matrix concept:
//! - Weighted directed graph transitions
//! - Multiple transitions from a single source coordinate
//! - Transition target retrieval by source
//! - Transition combined with Field constraints

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

// Assembly constraint primitives
extern int ck_even(int64_t *val);
extern int ck_range(int64_t *coord, int64_t min, int64_t max);

// Max transitions per source
#define MAX_TRANS 16

// Transition entry: (target_coord, weight)
typedef struct {
    int64_t target;
    double weight;
} Transition;

// Transition matrix: array of (source → transitions[])
typedef struct {
    int64_t source;
    Transition trans[MAX_TRANS];
    int count;
} TransitionRow;

// Simple transition store
static TransitionRow matrix[16];
static int row_count = 0;

static void add_transition(int64_t from, int64_t to, double weight) {
    // Find existing row or create new one
    for (int i = 0; i < row_count; i++) {
        if (matrix[i].source == from) {
            int n = matrix[i].count;
            if (n < MAX_TRANS) {
                matrix[i].trans[n].target = to;
                matrix[i].trans[n].weight = weight;
                matrix[i].count = n + 1;
            }
            return;
        }
    }
    // New row
    matrix[row_count].source = from;
    matrix[row_count].trans[0].target = to;
    matrix[row_count].trans[0].weight = weight;
    matrix[row_count].count = 1;
    row_count++;
}

// Get transition targets from source
static int get_transitions(int64_t from, int64_t *out_targets, double *out_weights, int max_out) {
    for (int i = 0; i < row_count; i++) {
        if (matrix[i].source == from) {
            int n = matrix[i].count < max_out ? matrix[i].count : max_out;
            for (int j = 0; j < n; j++) {
                out_targets[j] = matrix[i].trans[j].target;
                out_weights[j] = matrix[i].trans[j].weight;
            }
            return n;
        }
    }
    return 0;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-09-transition ===\n");
    printf("Concept: TransitionMatrix (weighted directed graph)\n\n");

    // ── 1. Basic transitions ──
    printf("1. Basic transitions (from 0 → 1 with w=0.8, 2 with w=0.2):\n");
    add_transition(0, 1, 0.8);
    add_transition(0, 2, 0.2);
    TEST("  Row count == 1", row_count == 1);
    int64_t targets[16];
    double weights[16];
    int n = get_transitions(0, targets, weights, 16);
    TEST("  Source 0 has 2 transitions", n == 2);
    TEST("  Target 1 present", n >= 1 && (targets[0] == 1 || targets[1] == 1));
    TEST("  Target 2 present", n >= 2 && (targets[0] == 2 || targets[1] == 2));
    TEST("  Weight 0.8 present", n >= 1 && (
         (targets[0] == 1 && weights[0] == 0.8) ||
         (targets[1] == 1 && weights[1] == 0.8)));
    TEST("  Weight 0.2 present", n >= 2 && (
         (targets[0] == 2 && weights[0] == 0.2) ||
         (targets[1] == 2 && weights[1] == 0.2)));

    // ── 2. Multiple sources ──
    printf("\n2. Multiple sources:\n");
    add_transition(1, 3, 1.0);
    add_transition(2, 4, 0.5);
    add_transition(2, 5, 0.5);
    TEST("  Row count == 3 (sources 0, 1, 2)", row_count == 3);

    n = get_transitions(1, targets, weights, 16);
    TEST("  Source 1 → 1 target", n == 1);
    TEST("  Source 1 → target 3", n >= 1 && targets[0] == 3);

    n = get_transitions(2, targets, weights, 16);
    TEST("  Source 2 → 2 targets", n == 2);

    n = get_transitions(99, targets, weights, 16);
    TEST("  Unknown source → 0 targets", n == 0);

    // ── 3. Transition + Field constraint ──
    printf("\n3. Transitions filtered by Even constraint:\n");
    // Source 0 has transitions to 1 (w=0.8) and 2 (w=0.2)
    // Even constraint on target: only 2 passes (even)
    n = get_transitions(0, targets, weights, 16);
    int even_count = 0;
    for (int i = 0; i < n; i++) {
        int64_t v = targets[i];
        if (ck_even(&v)) even_count++;
    }
    TEST("  Even filter: 1 of 2 transitions pass (2)", even_count == 1);

    // ── 4. Range + Even on transitions ──
    printf("\n4. Transitions with Range(0..3) + Even constraint:\n");
    // Source 2 has transitions to 4 and 5
    // Range(0..3) filter: neither 4 nor 5 passes
    // Even filter: 4 passes
    n = get_transitions(2, targets, weights, 16);
    int range_even_count = 0;
    for (int i = 0; i < n; i++) {
        int64_t v = targets[i];
        int in_range = ck_range(&v, 0, 3);
        int even = ck_even(&v);
        if (in_range && even) range_even_count++;
    }
    TEST("  Range(0..3)+Even: 0 transitions pass", range_even_count == 0);

    // Source 0 → target 1 fails Even, target 2 passes Even
    n = get_transitions(0, targets, weights, 16);
    range_even_count = 0;
    for (int i = 0; i < n; i++) {
        int64_t v = targets[i];
        int in_range = ck_range(&v, 0, 3);
        int even = ck_even(&v);
        if (in_range && even) range_even_count++;
    }
    TEST("  Source 0: 1 transition passes (2)", range_even_count == 1);

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
