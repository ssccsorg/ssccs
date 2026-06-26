//! SSCCS on RISC-V: concept-07-adjacency
//!
//! Cross-validates Adjacency and Memory Layout concepts:
//! - Structural relations: FourConnected grid adjacency
//! - Memory layout: row-major coordinate → logical address mapping
//! - Neighbor discovery from structural relations

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

// Row-major address: offset = y * stride + x
static int64_t row_major(int64_t x, int64_t y, int64_t stride) {
    return y * stride + x;
}

// FourConnected neighbors of (x, y) within bounds
// Returns number of valid neighbors
static int four_connected_neighbors(int64_t x, int64_t y, int64_t w, int64_t h,
                                     int64_t *out_x, int64_t *out_y, int max_out) {
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    int n = 0;
    for (int i = 0; i < 4 && n < max_out; i++) {
        int64_t nx = x + dx[i], ny = y + dy[i];
        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
            out_x[n] = nx;
            out_y[n] = ny;
            n++;
        }
    }
    return n;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-07-adjacency ===\n");
    printf("Concepts: Structural relations, memory layout\n\n");

    // ── 1. Memory layout: row-major ──
    printf("1. Row-major memory layout (stride=10):\n");
    int64_t stride = 10;
    TEST("  (0,0) → offset 0",  row_major(0, 0, stride) == 0);
    TEST("  (1,0) → offset 1",  row_major(1, 0, stride) == 1);
    TEST("  (0,1) → offset 10", row_major(0, 1, stride) == 10);
    TEST("  (2,3) → offset 32", row_major(2, 3, stride) == 32);
    TEST("  (9,9) → offset 99", row_major(9, 9, stride) == 99);

    // ── 2. FourConnected adjacency ──
    printf("\n2. FourConnected adjacency on 10x10 grid:\n");
    int grid_w = 10, grid_h = 10;

    // Center (5,5): all 4 neighbors valid
    int64_t nx[4], ny[4];
    int n = four_connected_neighbors(5, 5, grid_w, grid_h, nx, ny, 4);
    TEST("  Center (5,5): 4 neighbors", n == 4);

    // Check specific neighbor addresses
    int found_north = 0, found_south = 0, found_east = 0, found_west = 0;
    for (int i = 0; i < n; i++) {
        if (nx[i] == 5 && ny[i] == 4) found_north = 1; // N: (5,4)
        if (nx[i] == 5 && ny[i] == 6) found_south = 1; // S: (5,6)
        if (nx[i] == 6 && ny[i] == 5) found_east  = 1; // E: (6,5)
        if (nx[i] == 4 && ny[i] == 5) found_west  = 1; // W: (4,5)
    }
    TEST("  N neighbor (5,4) found", found_north);
    TEST("  S neighbor (5,6) found", found_south);
    TEST("  E neighbor (6,5) found", found_east);
    TEST("  W neighbor (4,5) found", found_west);

    // ── 3. Corner adjacency ──
    printf("\n3. Corner adjacency (boundary conditions):\n");
    n = four_connected_neighbors(0, 0, grid_w, grid_h, nx, ny, 4);
    TEST("  Corner (0,0): 2 neighbors (E, S)", n == 2);

    n = four_connected_neighbors(0, 9, grid_w, grid_h, nx, ny, 4);
    TEST("  Corner (0,9): 2 neighbors (E, N)", n == 2);

    n = four_connected_neighbors(9, 0, grid_w, grid_h, nx, ny, 4);
    TEST("  Corner (9,0): 2 neighbors (W, S)", n == 2);

    n = four_connected_neighbors(9, 9, grid_w, grid_h, nx, ny, 4);
    TEST("  Corner (9,9): 2 neighbors (W, N)", n == 2);

    // ── 4. Edge adjacency ──
    printf("\n4. Edge adjacency:\n");
    n = four_connected_neighbors(0, 5, grid_w, grid_h, nx, ny, 4);
    TEST("  Left edge (0,5): 3 neighbors (E, N, S)", n == 3);

    n = four_connected_neighbors(5, 0, grid_w, grid_h, nx, ny, 4);
    TEST("  Top edge (5,0): 3 neighbors (E, W, S)", n == 3);

    // ── 5. Structural relation as field constraint ──
    printf("\n5. Structural neighbors with Even field constraint:\n");
    // Grid (0..9, 0..9) with Even constraint on x-axis
    // Center (5,5): neighbors = (5,4), (5,6), (6,5), (4,5)
    // Even constraint on x: only (6,5) has even x → passes, (4,5) passes
    // (5,4) and (5,6) have odd x → fail
    int64_t center_x = 5, center_y = 5;
    n = four_connected_neighbors(center_x, center_y, grid_w, grid_h, nx, ny, 4);
    int even_pass_count = 0;
    for (int i = 0; i < n; i++) {
        if (nx[i] % 2 == 0) even_pass_count++; // Even constraint on x-axis
    }
    TEST("  Even constraint: 2 of 4 neighbors pass", even_pass_count == 2);

    // ── 6. Address distance (adjacent = close in memory) ──
    printf("\n6. Memory-proximate adjacency:\n");
    int64_t center_addr = row_major(5, 5, stride);
    for (int i = 0; i < n; i++) {
        int64_t neighbor_addr = row_major(nx[i], ny[i], stride);
        int64_t dist = neighbor_addr > center_addr ?
                       neighbor_addr - center_addr : center_addr - neighbor_addr;
        // All FourConnected neighbors are within 1 row (stride) of center
        char buf[64];
        snprintf(buf, sizeof(buf), "  Neighbor distance <= %lld", (long long)stride);
        TEST(buf, dist <= stride);
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
