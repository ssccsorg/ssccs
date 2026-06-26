//! SSCCS on RISC-V: concept-11-data-processing
//!
//! Cross-validates data processing via SSCCS observation:
//! - Matrix as Grid2D Scheme
//! - MatrixBoundary constraint (rows, cols)
//! - MatrixSumProjector (x + y as value)
//! - MatrixValueProjector (pre-computed values)
//! - Traditional vs observation-based summation

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

// Matrix boundary constraint: coord must be within (rows, cols)
static int matrix_boundary_allows(int64_t x, int64_t y, int64_t rows, int64_t cols) {
    return (x >= 0 && x < rows && y >= 0 && y < cols);
}

// Matrix sum projector: returns x + y as "value"
static int64_t matrix_sum_project(int64_t x, int64_t y) {
    return x + y;
}

// Matrix value projector: lookup from pre-computed array (row-major)
static int64_t matrix_value_project(int64_t row, int64_t col, int64_t cols,
                                     const int64_t *values) {
    return values[row * cols + col];
}

// SSCCS-style observation-based matrix summation
// 1. Scheme: Grid2D(rows, cols)
// 2. Field: MatrixBoundary(rows, cols)
// 3. Projector: MatrixValueProjector
// 4. observe_all: iterate all segments, filter by Field, project
static int64_t observe_matrix_sum(int64_t rows, int64_t cols, const int64_t *values) {
    int64_t sum = 0;
    for (int64_t x = 0; x < rows; x++) {
        for (int64_t y = 0; y < cols; y++) {
            // Field constraint: matrix boundary
            if (matrix_boundary_allows(x, y, rows, cols)) {
                // Projector: value lookup
                sum += matrix_value_project(x, y, cols, values);
            }
        }
    }
    return sum;
}

int main(void) {
    printf("=== SSCCS on RISC-V: concept-11-data-processing ===\n");
    printf("Data processing via observation-based computation\n\n");

    // 3x4 matrix
    int64_t rows = 3, cols = 4;
    int64_t matrix[] = {
        1,  2,  3,  4,
        5,  6,  7,  8,
        9, 10, 11, 12
    };
    int64_t traditional_sum = 0;
    for (int i = 0; i < rows * cols; i++) traditional_sum += matrix[i];

    // ── 1. Matrix boundary constraint ──
    printf("1. MatrixBoundary constraint (3x4):\n");
    TEST("  (0,0) in bounds", matrix_boundary_allows(0, 0, rows, cols));
    TEST("  (2,3) in bounds", matrix_boundary_allows(2, 3, rows, cols));
    TEST("  (3,0) out of bounds", !matrix_boundary_allows(3, 0, rows, cols));
    TEST("  (0,4) out of bounds", !matrix_boundary_allows(0, 4, rows, cols));
    TEST("  (-1,0) out of bounds", !matrix_boundary_allows(-1, 0, rows, cols));

    // ── 2. Matrix sum projector ──
    printf("\n2. MatrixSumProjector (x + y as value):\n");
    int64_t sum_xy = 0;
    for (int64_t x = 0; x < rows; x++) {
        for (int64_t y = 0; y < cols; y++) {
            sum_xy += matrix_sum_project(x, y);
        }
    }
    // Sum of (x+y) for 3x4: row0=0+1+2+3=6, row1=1+2+3+4=10, row2=2+3+4+5=14
    TEST("  Sum of (x+y) == 30", sum_xy == 30);

    // ── 3. Matrix value projector ──
    printf("\n3. MatrixValueProjector (value lookup):\n");
    TEST("  (0,0) = 1", matrix_value_project(0, 0, cols, matrix) == 1);
    TEST("  (1,2) = 7", matrix_value_project(1, 2, cols, matrix) == 7);
    TEST("  (2,3) = 12", matrix_value_project(2, 3, cols, matrix) == 12);

    // ── 4. Traditional vs observation summation ──
    printf("\n4. Traditional vs SSCCS observation summation:\n");
    int64_t obs_sum = observe_matrix_sum(rows, cols, matrix);
    TEST("  Traditional sum", traditional_sum == 78);
    TEST("  Observation sum", obs_sum == 78);
    TEST("  Results match", traditional_sum == obs_sum);

    // ── 5. Partial observation (subset of matrix) ──
    printf("\n5. Partial observation (first 2 rows only):\n");
    int64_t partial_sum = 0;
    for (int64_t x = 0; x < 2; x++) {
        for (int64_t y = 0; y < cols; y++) {
            if (matrix_boundary_allows(x, y, 2, cols)) {
                partial_sum += matrix_value_project(x, y, cols, matrix);
            }
        }
    }
    int64_t expected_partial = 1+2+3+4 + 5+6+7+8; // = 36
    TEST("  Partial sum (2 rows) == 36", partial_sum == expected_partial);

    // ── 6. Empty matrix ──
    printf("\n6. Edge case — 0xN matrix:\n");
    int64_t empty_sum = observe_matrix_sum(0, 4, matrix);
    TEST("  0x4 empty sum == 0", empty_sum == 0);

    // ── 7. Single element matrix ──
    printf("\n7. Edge case — 1x1 matrix:\n");
    int64_t single_val[] = {42};
    int64_t single_sum = observe_matrix_sum(1, 1, single_val);
    TEST("  1x1 sum == 42", single_sum == 42);

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
