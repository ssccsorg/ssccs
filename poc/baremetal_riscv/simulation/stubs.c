/*
 * SSCCS Spike Validation -- Stub implementations for external symbols
 *
 * These symbols are referenced (via la) by observe_full.S but defined
 * in Rust FFI. These stubs allow the C test to link and run under Spike.
 */

#include <stdint.h>

/* Constraint function pointer type matching Rust's ConstraintFn */
typedef uint32_t (*constraint_fn)(int64_t *);

/*
 * compose_and_fast: logical AND of two constraints.
 * Referenced via la in observe_full.S run_narrow.
 */
uint32_t compose_and_fast(constraint_fn fa, constraint_fn fb, int64_t *coord)
{
    return fa(coord) && fb(coord);
}

/*
 * compose_or_fast: logical OR of two constraints.
 * Referenced via la in observe_full.S run_broad.
 */
uint32_t compose_or_fast(constraint_fn fa, constraint_fn fb, int64_t *coord)
{
    return fa(coord) || fb(coord);
}
