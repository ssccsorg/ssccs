# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SSCCS COLLAPSE ENGINE — Multi-Segment Reduction in Silicon        ║
# ║                                                                    ║
# ║  Collapse = merge N segments into projection per Scheme rules.     ║
# ║  Implements custom2 opcode (funct3=001) reduction primitives.      ║
# ║                                                                    ║
# ║  Whitepaper §3.1:                                                  ║
# ║    Sum:      C(∪) = Σ w_i · C_i                                   ║
# ║    Product:  C(∩) = Π C_i                                         ║
# ║    Min/Max:  T(∪) = max(T_i),  T(∩) = min(T_i)                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

.section .text

# ═══════════════════════════════════════════════════════════════════════
# 1. COLLAPSE REDUCTION PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════

# ── 1.1 collapse_sum: Σ coords[0..n) ──
# Input:  a0 = *coords (i64 array), a1 = count
# Output: a0 = sum
.globl collapse_sum
collapse_sum:
    beqz    a1, .Lsum_zero
    mv      t3, a0
    li      t0, 0               # accumulator
    li      t4, 0               # index
.Lsum_loop:
    beq     t4, a1, .Lsum_done
    slli    t1, t4, 3
    add     t1, t3, t1
    ld      t2, 0(t1)
    add     t0, t0, t2
    addi    t4, t4, 1
    j       .Lsum_loop
.Lsum_done:
    mv      a0, t0
    ret
.Lsum_zero:
    li      a0, 0
    ret

# ── 1.2 collapse_min: min(coords[0..n)) ──
# Input:  a0 = *coords (i64 array), a1 = count
# Output: a0 = minimum value
.globl collapse_min
collapse_min:
    beqz    a1, .Lmin_zero
    mv      t3, a0
    ld      a0, 0(t3)           # initial min = first element
    li      t4, 1               # index
.Lmin_loop:
    beq     t4, a1, .Lmin_done
    slli    t1, t4, 3
    add     t1, t3, t1
    ld      t2, 0(t1)
    bge     t2, a0, .Lmin_skip
    mv      a0, t2
.Lmin_skip:
    addi    t4, t4, 1
    j       .Lmin_loop
.Lmin_done:
    ret
.Lmin_zero:
    li      a0, 0x7FFFFFFFFFFFFFFF   # i64::MAX sentinel
    ret

# ── 1.3 collapse_max: max(coords[0..n)) ──
# Input:  a0 = *coords (i64 array), a1 = count
# Output: a0 = maximum value
.globl collapse_max
collapse_max:
    beqz    a1, .Lmax_zero
    mv      t3, a0
    ld      a0, 0(t3)           # initial max = first element
    li      t4, 1               # index
.Lmax_loop:
    beq     t4, a1, .Lmax_done
    slli    t1, t4, 3
    add     t1, t3, t1
    ld      t2, 0(t1)
    ble     t2, a0, .Lmax_skip
    mv      a0, t2
.Lmax_skip:
    addi    t4, t4, 1
    j       .Lmax_loop
.Lmax_done:
    ret
.Lmax_zero:
    li      a0, 0x8000000000000000   # i64::MIN sentinel
    ret

# ── 1.4 collapse_product: Π coords[0..n) ──
# Input:  a0 = *coords (i64 array), a1 = count
# Output: a0 = product
.globl collapse_product
collapse_product:
    beqz    a1, .Lprod_zero
    mv      t3, a0
    li      t0, 1               # accumulator
    li      t4, 0               # index
.Lprod_loop:
    beq     t4, a1, .Lprod_done
    slli    t1, t4, 3
    add     t1, t3, t1
    ld      t2, 0(t1)
    mul     t0, t0, t2
    addi    t4, t4, 1
    j       .Lprod_loop
.Lprod_done:
    mv      a0, t0
    ret
.Lprod_zero:
    li      a0, 1
    ret

# ── 1.5 collapse_count: count of non-reject entries ──
# Input:  a0 = *results array, a1 = count, a2 = REJECT_SENTINEL
# Output: a0 = number of valid entries
.globl collapse_count
collapse_count:
    beqz    a1, .Lcnt_zero
    mv      t3, a0
    li      t0, 0
    li      t4, 0
.Lcnt_loop:
    beq     t4, a1, .Lcnt_done
    slli    t1, t4, 3
    add     t1, t3, t1
    ld      t2, 0(t1)
    beq     t2, a2, .Lcnt_skip
    addi    t0, t0, 1
.Lcnt_skip:
    addi    t4, t4, 1
    j       .Lcnt_loop
.Lcnt_done:
    mv      a0, t0
    ret
.Lcnt_zero:
    li      a0, 0
    ret

# ═══════════════════════════════════════════════════════════════════════
# 2. WEIGHTED COLLAPSE
# ═══════════════════════════════════════════════════════════════════════

# ── 2.1 collapse_weighted_sum: Σ w_i × coord_i ──
# Input:  a0 = *coords, a1 = *weights, a2 = count
# Output: a0 = Σ (coord_i × weight_i)
.globl collapse_weighted_sum
collapse_weighted_sum:
    beqz    a2, .Lws_zero
    mv      t3, a0              # coords base
    mv      t4, a1              # weights base
    li      t0, 0               # accumulator
    li      t5, 0               # index
.Lws_loop:
    beq     t5, a2, .Lws_done
    slli    t1, t5, 3
    add     t2, t3, t1;  ld t2, 0(t2)
    add     t1, t4, t1;  ld t1, 0(t1)
    mul     t2, t2, t1
    add     t0, t0, t2
    addi    t5, t5, 1
    j       .Lws_loop
.Lws_done:
    mv      a0, t0
    ret
.Lws_zero:
    li      a0, 0
    ret

# ── 2.2 collapse_weighted_avg: Σ (w_i × coord_i) / Σ w_i ──
.globl collapse_weighted_avg
collapse_weighted_avg:
    beqz    a2, .Lwa_zero
    mv      t3, a0
    mv      t4, a1
    li      t0, 0               # weighted sum
    li      t1, 0               # total weight
    li      t5, 0               # index
.Lwa_loop:
    beq     t5, a2, .Lwa_done
    slli    t6, t5, 3
    add     t2, t3, t6;  ld t2, 0(t2)
    add     t6, t4, t6;  ld t6, 0(t6)
    mul     t2, t2, t6
    add     t0, t0, t2
    add     t1, t1, t6
    addi    t5, t5, 1
    j       .Lwa_loop
.Lwa_done:
    beqz    t1, .Lwa_zero
    div     a0, t0, t1
    ret
.Lwa_zero:
    li      a0, 0
    ret

# ═══════════════════════════════════════════════════════════════════════
# 3. COLLAPSE PIPELINE
# ═══════════════════════════════════════════════════════════════════════

# ── 3.1 collapse: single group via reducer_fn ──
# Input:  a0 = *coords, a1 = count, a2 = reducer_fn
# Output: a0 = reducer(coords, count)
.globl collapse
collapse:
    addi    sp, sp, -16
    sd      ra, 8(sp)
    jalr    ra, a2, 0
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

# ── 3.2 collapse_batch: multiple groups ──
# Input:  a0 = *groups[], a1 = *counts[], a2 = num_groups,
#         a3 = reducer_fn, a4 = *out
.globl collapse_batch
collapse_batch:
    beqz    a2, .Lcb_done
    addi    sp, sp, -48
    sd      ra, 40(sp)
    sd      s0, 32(sp)
    sd      s1, 24(sp)
    sd      s2, 16(sp)
    sd      s3, 8(sp)
    sd      s4, 0(sp)

    mv      s0, a0
    mv      s1, a1
    mv      s2, a2
    mv      s3, a3
    mv      s4, a4

    li      t0, 0
.Lcb_loop:
    beq     t0, s2, .Lcb_exit
    slli    t1, t0, 3
    add     t2, s0, t1;  ld a0, 0(t2)
    add     t2, s1, t1;  ld a1, 0(t2)
    jalr    ra, s3, 0
    slli    t1, t0, 3
    add     t2, s4, t1;  sd a0, 0(t2)
    addi    t0, t0, 1
    j       .Lcb_loop

.Lcb_exit:
    ld      s4, 0(sp)
    ld      s3, 8(sp)
    ld      s2, 16(sp)
    ld      s1, 24(sp)
    ld      s0, 32(sp)
    ld      ra, 40(sp)
    addi    sp, sp, 48
    ret
.Lcb_done:
    ret

# ═══════════════════════════════════════════════════════════════════════
# 4. STATIC DATA
# ═══════════════════════════════════════════════════════════════════════

.section .rodata
.align 4

.globl COLLAPSE_SAMPLE_A
COLLAPSE_SAMPLE_A: .8byte 2, 4, 6, 8
.globl COLLAPSE_SAMPLE_B
COLLAPSE_SAMPLE_B: .8byte 1, 3, 5, 7
.globl COLLAPSE_COUNTS
COLLAPSE_COUNTS: .8byte 4, 4
.globl COLLAPSE_WEIGHTS_A
COLLAPSE_WEIGHTS_A: .8byte 1, 2, 1, 2
.globl COLLAPSE_WEIGHTS_B
COLLAPSE_WEIGHTS_B: .8byte 2, 1, 2, 1

# ═══════════════════════════════════════════════════════════════════════
# GOLDEN TEST ANCHORS
# ═══════════════════════════════════════════════════════════════════════
#
# GOLDEN_COLLAPSE_SUM_A: 20
# GOLDEN_COLLAPSE_SUM_B: 16
# GOLDEN_COLLAPSE_MIN_A: 2
# GOLDEN_COLLAPSE_MAX_B: 7
# GOLDEN_COLLAPSE_PROD_A: 384
# GOLDEN_COLLAPSE_COUNT_A: 4
# GOLDEN_COLLAPSE_WEIGHTED_SUM_A: 32
# GOLDEN_COLLAPSE_WEIGHTED_AVG_A: 5
