/*
 * SSCCS Spike Validation -- Stub implementations for external symbols
 *
 * These symbols are referenced (via la) by observe_full.S but defined
 * in Rust FFI. These stubs allow the C test to link and run under Spike.
 */

/* Constraint function pointer type matching Rust's ConstraintFn */
typedef int (*constraint_fn)(long long *);

/*
 * compose_and_fast: logical AND of two constraints.
 * Referenced via la in observe_full.S run_narrow.
 */
int compose_and_fast(constraint_fn fa, constraint_fn fb, long long *coord)
{
    return fa(coord) && fb(coord);
}

/*
 * compose_or_fast: logical OR of two constraints.
 * Referenced via la in observe_full.S run_broad.
 */
int compose_or_fast(constraint_fn fa, constraint_fn fb, long long *coord)
{
    return fa(coord) || fb(coord);
}
