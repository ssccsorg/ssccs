//! SSCCS on RISC-V: experiment-01-segment
//!
//! Cross-validates the Segment concept:
//! - Rust observe_all(): Field(no constraints) + Segment(coords) → identity projection
//! - RISC-V asm + Spike: same test in C harness, same expected result
//!
//! Segment concept: immutable coordinates + cryptographic identity.
//! Field: no constraints → all segments pass.
//! Projector: identity → returns the coordinate value.

#include <stdio.h>
#include <stdint.h>

static int total_passed = 0;
static int total_failed = 0;

// Coordinate → SegmentId (BLAKE3 hash of coordinate bytes)
// For simplicity, we use the coordinate value directly as identifier
// in this C harness. Full BLAKE3 hashing would require a library.

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

// Constraint: no constraints → always pass
static int field_allows(int64_t coord) {
    (void)coord;
    return 1; // no constraints → always allowed
}

// Identity projector: returns the coordinate value
static int64_t project_identity(int64_t coord) {
    return coord;
}

// Observation: field_allows(coord) ? project_identity(coord) : REJECT
// REJECT represented as -1 (since coordinates are non-negative in our tests)
static int64_t observe(int64_t coord) {
    if (field_allows(coord)) {
        return project_identity(coord);
    }
    return -1; // REJECT sentinel
}

int main(void) {
    printf("=== SSCCS on RISC-V: experiment-01-segment ===\n");
    printf("Concept: Segment (immutable coordinate + identity projection)\n");
    printf("Field: no constraints\n");
    printf("Projector: identity\n\n");

    // Test coordinates: [0, 2, 4, 6, 8, 10]
    // Range is arbitrary; Segment accepts any coordinate value.
    int64_t test_coords[] = {0, 2, 4, 6, 8, 10};
    int num_coords = sizeof(test_coords) / sizeof(test_coords[0]);
    int64_t expected[] = {0, 2, 4, 6, 8, 10};

    printf("Segments under test:\n");
    for (int i = 0; i < num_coords; i++) {
        printf("  coord=%lld\n", (long long)test_coords[i]);
    }
    printf("\n");

    // Observe each segment
    for (int i = 0; i < num_coords; i++) {
        int64_t result = observe(test_coords[i]);
        char buf[64];
        snprintf(buf, sizeof(buf), "observe(coord=%lld) == %lld",
                 (long long)test_coords[i], (long long)expected[i]);
        TEST(buf, result == expected[i]);
    }

    printf("\n");
    printf("Total:  %d\n", total_passed + total_failed);
    printf("Passed: %d\n", total_passed);
    printf("Failed: %d\n", total_failed);

    return total_failed > 0 ? 1 : 0;
}
