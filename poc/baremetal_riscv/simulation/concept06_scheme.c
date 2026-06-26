//! SSCCS on RISC-V: concept-06-scheme
//!
//! Cross-validates the Scheme concept:
//! - Grid2D: 2D grid with FourConnected adjacency
//! - IntegerLine: 1D line with range
//! - Memory mapping: coordinate → logical address
//! - Segment containment

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

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

// map 2D coordinates to linear address (row-major)
static int64_t grid_addr(int64_t x, int64_t y, int64_t width) {
    return y * width + x;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-06-scheme ===\n");
    printf("Templates: Grid2D, IntegerLine\n\n");

    // ── 1. Grid2D 5x5 FourConnected ──
    printf("1. Grid2D 5x5 (FourConnected):\n");
    int grid_w = 5, grid_h = 5;
    int total_segments = grid_w * grid_h;
    TEST("  Total segments == 25", total_segments == 25);

    // Row-major memory layout: (y, x) → y * width + x
    int64_t origin_addr = grid_addr(0, 0, grid_w);
    int64_t center_addr = grid_addr(2, 2, grid_w);
    TEST("  Origin (0,0) address == 0", origin_addr == 0);
    TEST("  Center (2,2) address == 12", center_addr == 12); // 2*5+2

    // Adjacency: FourConnected → NSEW neighbors
    // Center (2,2) neighbors: N(2,1), S(2,3), E(3,2), W(1,2)
    int cx = 2, cy = 2;
    int neighbors[4][2] = {{cx, cy-1}, {cx, cy+1}, {cx+1, cy}, {cx-1, cy}};
    int64_t expected_addrs[] = {7, 17, 13, 11}; // row-major addresses
    int valid_neighbors = 0;
    for (int i = 0; i < 4; i++) {
        int nx = neighbors[i][0], ny = neighbors[i][1];
        if (nx >= 0 && nx < grid_w && ny >= 0 && ny < grid_h) {
            int64_t addr = grid_addr(nx, ny, grid_w);
            TEST("  Neighbor address matches", addr == expected_addrs[i]);
            valid_neighbors++;
        }
    }
    TEST("  All 4 neighbors valid", valid_neighbors == 4);

    // ── 2. IntegerLine -5..5 step 1 ──
    printf("\n2. IntegerLine (-5..5, step 1):\n");
    int line_min = -5, line_max = 5, line_step = 1;
    int line_count = 0;
    for (int i = line_min; i <= line_max; i += line_step) line_count++;
    TEST("  Segment count == 11", line_count == 11);

    // Memory mapping: offset = (value - min) / step
    TEST("  coord -5 → offset 0", ((-5 - line_min) / line_step) == 0);
    TEST("  coord 0  → offset 5", ((0 - line_min) / line_step) == 5);
    TEST("  coord 5  → offset 10", ((5 - line_min) / line_step) == 10);
    TEST("  coord 3  → offset 8", ((3 - line_min) / line_step) == 8);

    // ── 3. Segment containment ──
    printf("\n3. Segment containment:\n");
    // Grid2D: coord [0..4, 0..4]
    TEST("  (2,2) in grid", (2 >= 0 && 2 < grid_w && 2 >= 0 && 2 < grid_h));
    TEST("  (5,2) NOT in grid", !(5 >= 0 && 5 < grid_w));
    TEST("  (-1,0) NOT in grid", !(-1 >= 0 && -1 < grid_w));
    // IntegerLine: coord [-5..5]
    TEST("  0 in line", (0 >= line_min && 0 <= line_max));
    TEST("  -5 in line", (-5 >= line_min && -5 <= line_max));
    TEST("  6 NOT in line", !(6 >= line_min && 6 <= line_max));

    // ── 4. Grid2D + Field constraint ──
    printf("\n4. Grid2D with Even constraint on x-axis:\n");
    // Field: Even(x) where x = axis 0
    // Grid (0..4, 0..4): even x values = {0, 2, 4}
    int even_pass = 0, even_total = 0;
    for (int y = 0; y < grid_h; y++) {
        for (int x = 0; x < grid_w; x++) {
            int x_even = (x % 2 == 0);
            even_total++;
            if (x_even) even_pass++;
        }
    }
    TEST("  Even constraint: 3/5 columns pass", even_pass == 3 * grid_h); // 3 cols × 5 rows
    (void)even_total;

    // ── 5. Grid2D sum projector ──
    printf("\n5. Grid2D with sum projector:\n");
    // For center (2,2): sum = 2+2 = 4
    int64_t center_sum = 2 + 2;
    TEST("  Center (2,2) sum == 4", center_sum == 4);
    // For four corners
    int64_t corners_sum[] = {0+0, 0+4, 4+0, 4+4};
    TEST("  (0,0) sum == 0", corners_sum[0] == 0);
    TEST("  (0,4) sum == 4", corners_sum[1] == 4);
    TEST("  (4,0) sum == 4", corners_sum[2] == 4);
    TEST("  (4,4) sum == 8", corners_sum[3] == 8);

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
