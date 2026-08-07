/*
 * SSCCS Spike Runtime Validation — Collapse, Field, Layout, Adjacency
 *
 * Calls the assembly modules collapse.S, field_update.S, scheme_layout.S,
 * and scheme_adjacency.S under Spike + pk, and validates their outputs
 * against the golden anchors documented in each .S file.
 *
 * This is the runtime complement of the assembly syntax gate: the gate
 * proves every module assembles, this harness proves the modules execute
 * correctly on the ISA.
 */

#include <stdio.h>
#include <stdint.h>

/* ── collapse.S ── */
extern long long collapse_sum(long long *coords, long long count);
extern long long collapse_min(long long *coords, long long count);
extern long long collapse_max(long long *coords, long long count);
extern long long collapse_product(long long *coords, long long count);
extern long long collapse_count(long long *results, long long count, long long sentinel);
extern long long collapse_weighted_sum(long long *coords, long long *weights, long long count);
extern long long collapse_weighted_avg(long long *coords, long long *weights, long long count);
extern long long collapse(long long *coords, long long count,
                          long long (*reducer)(long long *, long long));

/* ── field_update.S ──
 * Field state layout expected by the assembly primitives:
 *   offset 0:   constraint_fn_ptrs[8]
 *   offset 64:  constraint_ids[8] (u32)
 *   offset 96:  transitions[16] of {from, to, weight} (24 bytes each)
 *   offset 480: num_constraints (u32)
 *   offset 484: num_transitions (u32)
 */
typedef struct {
    unsigned long long constraint_fns[8];
    unsigned int constraint_ids[8];
    struct {
        long long from;
        long long to;
        long long weight;
    } transitions[16];
    unsigned int num_constraints;
    unsigned int num_transitions;
} FieldState;

extern long long field_add_constraint(FieldState *f, unsigned long long fn, unsigned int id);
extern long long field_remove_constraint(FieldState *f, unsigned int id);
extern void field_clear(FieldState *f);
extern long long field_add_transition(FieldState *f, long long from, long long to,
                                      long long weight);
extern long long field_update_weight(FieldState *f, long long from, long long to,
                                     long long weight);
extern long long field_get_transitions(FieldState *f, long long from, long long *out);

/* ── scheme_layout.S ── */
extern long long layout_linear_1d(long long coord, long long stride);
extern long long layout_linear_nd(long long *coords, long long *strides, unsigned int dims);
extern long long layout_row_major_2d(long long x, long long y, long long width,
                                     long long elem_size);
extern long long layout_row_major_3d(long long x, long long y, long long z,
                                     long long width, long long height,
                                     long long elem_size);
extern long long layout_col_major_2d(long long x, long long y, long long height,
                                     long long elem_size);
extern long long morton_encode_2d(long long x, long long y);
extern long long layout_zorder_2d(long long x, long long y, long long elem_size);

/* ── scheme_adjacency.S ── */
extern long long adj_grid_4(long long x, long long y, long long min_x, long long max_x,
                            long long min_y, long long max_y, long long *out);
extern long long adj_grid_8(long long x, long long y, long long min_x, long long max_x,
                            long long min_y, long long max_y, long long *out);
extern long long adj_manhattan_1d(long long coord, long long dist, long long min_coord,
                                  long long max_coord, long long *out);
extern long long adj_graph_edges(long long *edge_pairs, long long num_edges,
                                 long long from_id, long long *out);

/* observe_full.S emits this sentinel for rejected observations. */
#define REJECT_SENTINEL (0x8000000000000000LL)

static int total_passed = 0;
static int total_failed = 0;

#define TEST(name, cond, expected, actual)                              \
    do {                                                                \
        long long exp_ = (long long)(expected);                         \
        long long act_ = (long long)(actual);                           \
        if ((cond)) {                                                   \
            printf("PASS: %s\n", (name));                              \
            total_passed++;                                             \
        } else {                                                        \
            printf("FAIL: %s (expected %lld, got %lld)\n",             \
                   (name), exp_, act_);                                 \
            total_failed++;                                             \
        }                                                               \
    } while (0)

static unsigned int dummy_constraint(long long *c)
{
    (void)c;
    return 1;
}

int main(void)
{
    long long r;

    printf("-- collapse --\n");
    {
        long long a[4] = {2, 4, 6, 8};
        long long b[4] = {1, 3, 5, 7};
        long long w_a[4] = {1, 2, 1, 2};
        long long results[4] = {2, REJECT_SENTINEL, REJECT_SENTINEL, 10};

        r = collapse_sum(a, 4);
        TEST("collapse_sum(A)", r == 20, 20, r);
        r = collapse_sum(b, 4);
        TEST("collapse_sum(B)", r == 16, 16, r);
        r = collapse_min(a, 4);
        TEST("collapse_min(A)", r == 2, 2, r);
        r = collapse_max(b, 4);
        TEST("collapse_max(B)", r == 7, 7, r);
        r = collapse_product(a, 4);
        TEST("collapse_product(A)", r == 384, 384, r);
        r = collapse_count(results, 4, REJECT_SENTINEL);
        TEST("collapse_count", r == 2, 2, r);
        r = collapse_weighted_sum(a, w_a, 4);
        TEST("collapse_weighted_sum(A)", r == 32, 32, r);
        r = collapse_weighted_avg(a, w_a, 4);
        TEST("collapse_weighted_avg(A)", r == 5, 5, r);
        r = collapse(a, 4, collapse_sum);
        TEST("collapse(sum, A)", r == 20, 20, r);
    }

    printf("\n-- field update --\n");
    {
        FieldState fs = {0};
        unsigned long long fn = (unsigned long long)(uintptr_t)dummy_constraint;

        r = field_add_constraint(&fs, fn, 7);
        TEST("field_add_constraint", r == 0, 0, r);
        TEST("num_constraints", fs.num_constraints == 1, 1, fs.num_constraints);
        r = field_add_constraint(&fs, fn, 8);
        TEST("field_add_constraint#2", r == 0, 0, r);
        r = field_remove_constraint(&fs, 7);
        TEST("field_remove_constraint", r == 0, 0, r);
        TEST("num_constraints after remove", fs.num_constraints == 1, 1,
             fs.num_constraints);
        field_clear(&fs);
        TEST("field_clear", fs.num_constraints == 0, 0, fs.num_constraints);

        r = field_add_transition(&fs, 1, 2, 10);
        TEST("field_add_transition", r == 0, 0, r);
        r = field_update_weight(&fs, 1, 2, 99);
        TEST("field_update_weight", r == 0, 0, r);
        r = field_update_weight(&fs, 9, 2, 1);
        TEST("field_update_weight(miss)", r == -1, -1, r);
        {
            long long out[32] = {0};
            r = field_get_transitions(&fs, 1, out);
            TEST("field_get_transitions count", r == 1, 1, r);
            TEST("field_get_transitions to", out[0] == 2, 2, out[0]);
            TEST("field_get_transitions weight", out[1] == 99, 99, out[1]);
        }
    }

    printf("\n-- scheme layout --\n");
    {
        long long coords[2] = {1, 2};
        long long strides[2] = {10, 20};

        r = layout_linear_1d(6, 7);
        TEST("layout_linear_1d", r == 42, 42, r);
        r = layout_linear_nd(coords, strides, 2);
        TEST("layout_linear_nd", r == 50, 50, r);
        r = layout_row_major_2d(2, 5, 8, 1);
        TEST("layout_row_major_2d", r == 42, 42, r);
        r = layout_row_major_3d(1, 2, 3, 4, 5, 2);
        TEST("layout_row_major_3d", r == 138, 138, r);
        r = layout_col_major_2d(3, 4, 10, 1);
        TEST("layout_col_major_2d", r == 34, 34, r);
        r = morton_encode_2d(1, 2);
        TEST("morton_encode_2d", r == 9, 9, r);
        r = layout_zorder_2d(1, 2, 1);
        TEST("layout_zorder_2d", r == 9, 9, r);
    }

    printf("\n-- scheme adjacency --\n");
    {
        long long out[16] = {0};
        r = adj_grid_4(2, 2, 0, 4, 0, 4, out);
        TEST("adj_grid_4(center)", r == 4, 4, r);
        r = adj_grid_4(0, 0, 0, 4, 0, 4, out);
        TEST("adj_grid_4(corner)", r == 2, 2, r);
        r = adj_grid_8(2, 2, 0, 4, 0, 4, out);
        TEST("adj_grid_8(center)", r == 8, 8, r);
        r = adj_grid_8(0, 0, 0, 4, 0, 4, out);
        TEST("adj_grid_8(corner)", r == 3, 3, r);
    }
    {
        long long out[8] = {0};
        r = adj_manhattan_1d(5, 1, 0, 10, out);
        TEST("adj_manhattan_1d(d1)", r == 2, 2, r);
        r = adj_manhattan_1d(5, 2, 0, 10, out);
        TEST("adj_manhattan_1d(d2)", r == 4, 4, r);
    }
    {
        long long edges[6] = {1, 2, 1, 3, 2, 4};
        long long out[8] = {0};
        r = adj_graph_edges(edges, 3, 1, out);
        TEST("adj_graph_edges count", r == 2, 2, r);
        TEST("adj_graph_edges to0", out[0] == 2, 2, out[0]);
        TEST("adj_graph_edges to1", out[1] == 3, 3, out[1]);
    }

    printf("\n=== SUMMARY ===\n");
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);
    printf("Total:  %d\n", total_passed + total_failed);

    return total_failed > 0 ? 1 : 0;
}
