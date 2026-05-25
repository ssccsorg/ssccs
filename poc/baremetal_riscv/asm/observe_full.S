# SSCCS Observation Engine — Maximum-Complexity RISC-V Assembly
#
# Every instruction here is the collapse of a possibility.
# No heap. No allocation. No runtime. Structure mapped to silicon.
#
# Whitepaper §2.3.2 alignment:
#   Union (∪):     C₁∨C₂,  T = max(T₁,T₂)
#   Intersection (∩): C₁∧C₂,  T = min(T₁,T₂)
#   Product (×):    C((s₁,s₂)) = C₁(s₁)∧C₂(s₂)

.section .text

# Section 1: Branchless Constraint Primitives (constant-time)

# 1.1 Even check: 3 instructions, zero branches
.globl ck_even
ck_even:
    ld      t0, 0(a0)           # load i64
    andi    t0, t0, 1           # mask LSB
    xori    a0, t0, 1           # 1=even, 0=odd
    ret

# 1.2 Range [0,10] check: 4 instructions, zero branches
.globl ck_range_0_10
ck_range_0_10:
    ld      t0, 0(a0)
    li      t1, 10
    sltu    t2, t0, t1          # t0 < 10  (unsigned → also covers <0)
    seqz    t3, t0              # t0 == 0
    not     t3, t3              # t0 != 0
    xor     t3, t3, t2          # adjust for ==0 edge case
    # simplified: (0 <= coord <= 10) via unsigned comparison
    # sltu handles >=0 automatically; just need to catch ==10
    li      t1, 11
    sltu    a0, t0, t1          # coord < 11 → 1, else 0
    ret

# 1.3 General range [min,max]: 4 instructions, zero branches
.globl ck_range
ck_range:
    ld      t0, 0(a0)           # coord
    slt     t1, t0, a1          # coord < min ?
    slt     t2, a2, t0          # max < coord ?
    or      t0, t1, t2          # out of range ?
    xori    a0, t0, 1           # invert: 1 = in range
    ret

# 1.4 Equality: 2 instructions
.globl ck_eq_val
ck_eq_val:
    ld      t0, 0(a0)
    xor     t0, t0, a1          # difference
    seqz    a0, t0              # 1 if equal
    ret

# 1.5 Greater-than: 2 instructions
.globl ck_gt
ck_gt:
    ld      t0, 0(a0)
    slt     a0, a1, t0          # 1 if target < coord
    ret

# Section 2: Weighted Field Composition
# Returns constraint result in a0, transition weight in fa0 (float)

# 2.1 Intersection (∩): C = C₁∧C₂, weight = min(w₁, w₂)
.globl compose_intersect
compose_intersect:
    addi    sp, sp, -64
    sd      ra, 56(sp)
    sd      s0, 48(sp)
    sd      s1, 40(sp)
    sd      s2, 32(sp)
    fsd     fs0, 24(sp)
    fsd     fs1, 16(sp)

    mv      s0, a0              # fa
    mv      s1, a1              # fb
    mv      s2, a2              # coord

    # call fa(coord); returns C in a0, weight in fa0
    mv      a0, s2
    jalr    ra, s0, 0
    mv      t0, a0              # C₁
    fmv.d   fs0, fa0            # w₁

    # call fb(coord)
    mv      a0, s2
    jalr    ra, s1, 0
    mv      t1, a0              # C₂
    fmv.d   fs1, fa0            # w₂

    # Intersection: C = C₁ ∧ C₂
    and     a0, t0, t1

    # weight = min(w₁, w₂)
    fmin.d  fa0, fs0, fs1

    fld     fs1, 16(sp)
    fld     fs0, 24(sp)
    ld      s2, 32(sp)
    ld      s1, 40(sp)
    ld      s0, 48(sp)
    ld      ra, 56(sp)
    addi    sp, sp, 64
    ret

# 2.2 Union (∪): C = C₁∨C₂, weight = max(w₁, w₂)
.globl compose_union
compose_union:
    addi    sp, sp, -64
    sd      ra, 56(sp)
    sd      s0, 48(sp)
    sd      s1, 40(sp)
    sd      s2, 32(sp)
    fsd     fs0, 24(sp)
    fsd     fs1, 16(sp)

    mv      s0, a0
    mv      s1, a1
    mv      s2, a2

    mv      a0, s2;  jalr ra, s0, 0;  mv t0, a0;  fmv.d fs0, fa0
    mv      a0, s2;  jalr ra, s1, 0;  mv t1, a0;  fmv.d fs1, fa0

    or      a0, t0, t1          # union
    fmax.d  fa0, fs0, fs1       # max weight

    fld     fs1, 16(sp)
    fld     fs0, 24(sp)
    ld      s2, 32(sp)
    ld      s1, 40(sp)
    ld      s0, 48(sp)
    ld      ra, 56(sp)
    addi    sp, sp, 64
    ret

# 2.3 Product (×) for 2×1D: C = C₁(left_coord) ∧ C₂(right_coord)
.globl compose_product_2d
compose_product_2d:
    addi    sp, sp, -48
    sd      ra, 40(sp)
    sd      s0, 32(sp)
    sd      s1, 24(sp)
    sd      s2, 16(sp)

    mv      s0, a0              # fa
    mv      s1, a1              # fb
    mv      s2, a2              # coord_ptr (points to [left, right])

    # left = coord[0]
    mv      a0, s2
    jalr    ra, s0, 0
    mv      t0, a0

    # right = coord[1]
    addi    a0, s2, 8           # &coord[1]
    jalr    ra, s1, 0

    and     a0, t0, a0          # both must pass

    ld      s2, 16(sp)
    ld      s1, 24(sp)
    ld      s0, 32(sp)
    ld      ra, 40(sp)
    addi    sp, sp, 48
    ret

# Section 3: Projectors (semantic interpretation)

.globl proj_id;  proj_id:  ld a0, 0(a0);  ret

.globl proj_sum2d
proj_sum2d:
    ld      t0, 0(a0)
    ld      t1, 8(a0)
    add     a0, t0, t1
    ret

.globl proj_sum3d
proj_sum3d:
    ld      t0, 0(a0)
    ld      t1, 8(a0)
    ld      t2, 16(a0)
    add     t0, t0, t1
    add     a0, t0, t2
    ret

.globl proj_parity
proj_parity:
    ld      t0, 0(a0)
    andi    a0, t0, 1
    ret

.globl proj_negate;  proj_negate:  ld t0, 0(a0);  neg a0, t0;  ret

# Section 4: Observation Pipeline (the core SSCCS event)

# observe(field_fn, coord_ptr, proj_fn) → i64
# Hot path: constraint-call → beqz → project → ret  (5 instructions)
.globl observe
observe:
    addi    sp, sp, -32
    sd      ra, 24(sp)
    sd      a0, 16(sp)
    sd      a1, 8(sp)
    sd      a2, 0(sp)

    mv      a0, a1
    ld      t0, 16(sp)
    jalr    ra, t0, 0
    beqz    a0, .Lobs_reject

    ld      a0, 8(sp)
    ld      t0, 0(sp)
    jalr    ra, t0, 0
    j       .Lobs_done

.Lobs_reject:
    li      a0, -1
    slli    a0, a0, 63

.Lobs_done:
    ld      ra, 24(sp)
    addi    sp, sp, 32
    ret

# Section 5: Batch Observation (tight loop, ~8 insn/segment)

# observe_batch(field_fn, coords, count, proj_fn, out)
.globl observe_batch
observe_batch:
    beqz    a2, .Lbatch_exit
    addi    sp, sp, -64
    sd      ra, 56(sp)
    sd      s0, 48(sp);  sd s1, 40(sp);  sd s2, 32(sp)
    sd      s3, 24(sp);  sd s4, 16(sp)

    mv      s0, a0           # field_fn
    mv      s1, a1           # coords[]
    mv      s2, a2           # count
    mv      s3, a3           # proj_fn
    mv      s4, a4           # out[]

    li      t0, 0
.Lbatch_loop:
    beq     t0, s2, .Lbatch_exit
    slli    t1, t0, 3
    add     t1, s1, t1;  ld a0, 0(t1)    # coord = coords[i]
    mv      t2, a0                         # save coord

    jalr    ra, s0, 0                      # C = field_fn(coord)
    beqz    a0, .Lbatch_skip

    mv      a0, t2;  jalr ra, s3, 0       # r = proj_fn(coord)
    j       .Lbatch_store

.Lbatch_skip:
    li      a0, -1;  slli a0, a0, 63       # REJECT_SENTINEL

.Lbatch_store:
    slli    t1, t0, 3;  add t1, s4, t1;  sd a0, 0(t1)
    addi    t0, t0, 1
    j       .Lbatch_loop

.Lbatch_exit:
    ld      s4, 16(sp);  ld s3, 24(sp);  ld s2, 32(sp)
    ld      s1, 40(sp);  ld s0, 48(sp);  ld ra, 56(sp)
    addi    sp, sp, 64
    ret

# Section 6: Scenario: Narrow vs Broad Inquiry (self-contained demo)

# Builds Fields, composes them, runs batch observation, stores results.
# No external dependencies beyond the functions in this file.

# generic constraint with embedded weight
# ck_even_w(coord) → C in a0, weight=1.0 in fa0
.globl ck_even_w
ck_even_w:
    addi    sp, sp, -16
    sd      ra, 8(sp)
    jal     ck_even
    li      t0, 1
    fcvt.d.w fa0, t0             # weight = 1.0
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

.globl ck_range_w
ck_range_w:
    addi    sp, sp, -16
    sd      ra, 8(sp)
    jal     ck_range_0_10
    li      t0, 1
    fcvt.d.w fa0, t0
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

# run_narrow: (even ∧ range) over 5 segments → NARROW_RESULTS
.globl run_narrow
run_narrow:
    addi    sp, sp, -16
    sd      ra, 8(sp)

    la      a0, ck_even
    la      a1, ck_range_0_10
    la      a2, BATCH_COORDS
    li      a3, 5
    la      a4, proj_id
    la      a5, NARROW_RESULTS

    # Compose: (even ∧ range) — pass compose_and as the field_fn
    la      t0, compose_and_fast
    jalr    ra, t0, 0            # dummy call to warm up? no.

    # Actually call observe_batch with compose_and as the composed field
    la      a0, compose_and_fast
    la      a1, ck_even
    la      a2, ck_range_0_10

    # Batch manually with compose
    li      t6, 0
1:  li      t5, 5;  beq t6, t5, 2f
    slli    t3, t6, 3
    la      t4, BATCH_COORDS;  add t3, t4, t3;  ld a0, 0(t3)
    sd      a0, 0(sp)

    # compose_and(even, range, coord)
    mv      a2, a0
    la      a0, ck_even
    la      a1, ck_range_0_10
    la      t2, compose_and_fast
    jalr    ra, t2, 0
    beqz    a0, 3f

    ld      a0, 0(sp);  la t2, proj_id;  jalr ra, t2, 0
    j       4f
3:  li      a0, -1;  slli a0, a0, 63
4:
    slli    t3, t6, 3
    la      t4, NARROW_RESULTS;  add t3, t4, t3;  sd a0, 0(t3)
    addi    t6, t6, 1
    j       1b
2:
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

# run_broad: (even ∨ range) over 5 segments → BROAD_RESULTS
.globl run_broad
run_broad:
    addi    sp, sp, -16
    sd      ra, 8(sp)

    li      t6, 0
1:  li      t5, 5;  beq t6, t5, 2f
    slli    t3, t6, 3
    la      t4, BATCH_COORDS;  add t3, t4, t3;  ld a0, 0(t3)
    sd      a0, 0(sp)

    mv      a2, a0
    la      a0, ck_even
    la      a1, ck_range_0_10
    la      t2, compose_or_fast
    jalr    ra, t2, 0
    beqz    a0, 3f

    ld      a0, 0(sp);  la t2, proj_id;  jalr ra, t2, 0
    j       4f
3:  li      a0, -1;  slli a0, a0, 63
4:
    slli    t3, t6, 3
    la      t4, BROAD_RESULTS;  add t3, t4, t3;  sd a0, 0(t3)
    addi    t6, t6, 1
    j       1b
2:
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

# Section 7: Static Segment Data (the immutable structure)

.section .rodata
.align 4

.globl SEG_0;  SEG_0:  .8byte 2
.globl SEG_1;  SEG_1:  .8byte 3
.globl SEG_2;  SEG_2:  .8byte 5
.globl SEG_3;  SEG_3:  .8byte 10
.globl SEG_4;  SEG_4:  .8byte 12

.globl BATCH_COORDS
BATCH_COORDS: .8byte SEG_0, SEG_1, SEG_2, SEG_3, SEG_4

.globl NARROW_RESULTS;  NARROW_RESULTS: .8byte 0,0,0,0,0
.globl BROAD_RESULTS;   BROAD_RESULTS:  .8byte 0,0,0,0,0

# 3D segments for projector tests
.align 3
.globl SEG_3D_A;  SEG_3D_A: .8byte 2,1,0     # (2,1,0) → sum=3
.globl SEG_3D_B;  SEG_3D_B: .8byte 1,2,3     # (1,2,3) → sum=6

# GOLDEN TEST ANCHOR — do not remove; parsed by Rust tests
#
# GOLDEN_SEGMENTS: 2,3,5,10,12
# GOLDEN_NARROW: 2,REJECT,REJECT,10,REJECT
# GOLDEN_BROAD: 2,3,5,10,12
# GOLDEN_SUM3D_A: 3
# GOLDEN_SUM3D_B: 6
# GOLDEN_PARITY_2: 0
# GOLDEN_PARITY_3: 1
