# SSCCS Core Concepts — RISC-V Assembly
#
# Implements the observation flow directly in hardware instructions.
#
#   Segment (read-only coordinates) ─┐
#   Field (constraint-check code)  ──┤→ observe → projection or reject
#   Projector (interpretation code) ─┘
#
# This is the SSCCS philosophy at the hardware level:
# "computation is observation of structure, not sequential instruction execution."
#
# ABI: a0 = arg0 / return, a1 = arg1, a2 = arg2

.section .text

# ── check_even(coord_ptr) → bool
.globl check_even
check_even:
    lw      t0, 0(a0)
    andi    t0, t0, 1
    xori    a0, t0, 1
    ret

# ── check_range_0_10(coord_ptr) → bool
.globl check_range_0_10
check_range_0_10:
    lw      t0, 0(a0)
    bltz    t0, .Lrange_fail
    li      t1, 10
    bgt     t0, t1, .Lrange_fail
    li      a0, 1
    ret
.Lrange_fail:
    li      a0, 0
    ret

# ── compose_and(fa, fb, coord) → bool
.globl compose_and
compose_and:
    addi    sp, sp, -32
    sw      ra, 28(sp)
    sw      a0, 24(sp)
    sw      a1, 20(sp)
    sw      a2, 16(sp)

    mv      a0, a2
    lw      t0, 24(sp)
    jalr    ra, t0, 0
    sw      a0, 12(sp)

    lw      a0, 16(sp)
    lw      t0, 20(sp)
    jalr    ra, t0, 0

    lw      t0, 12(sp)
    and     a0, a0, t0

    lw      ra, 28(sp)
    addi    sp, sp, 32
    ret

# ── compose_or(fa, fb, coord) → bool
.globl compose_or
compose_or:
    addi    sp, sp, -32
    sw      ra, 28(sp)
    sw      a0, 24(sp)
    sw      a1, 20(sp)
    sw      a2, 16(sp)

    mv      a0, a2
    lw      t0, 24(sp)
    jalr    ra, t0, 0
    sw      a0, 12(sp)

    lw      a0, 16(sp)
    lw      t0, 20(sp)
    jalr    ra, t0, 0

    lw      t0, 12(sp)
    or      a0, a0, t0

    lw      ra, 28(sp)
    addi    sp, sp, 32
    ret

# ── projector_identity(coord_ptr) → i64
.globl projector_identity
projector_identity:
    lw      a0, 0(a0)
    ret

# ── observe(field_fn, coord_ptr, projector_fn) → i64
#     Returns REJECT_SENTINEL (0x8000000000000000) on constraint failure.
.globl observe
observe:
    addi    sp, sp, -32
    sw      ra, 28(sp)
    sw      a0, 24(sp)
    sw      a1, 16(sp)
    sw      a2, 20(sp)

    # call field_fn(coord)
    mv      a0, a1
    lw      t0, 24(sp)
    jalr    ra, t0, 0
    beqz    a0, .Lreject

    # call projector_fn(coord)
    lw      a0, 16(sp)
    lw      t0, 20(sp)
    jalr    ra, t0, 0
    j       .Ldone

.Lreject:
    li      a0, -1
    slli    a0, a0, 63

.Ldone:
    lw      ra, 28(sp)
    addi    sp, sp, 32
    ret

# ── static segments ──
.section .rodata
.align 3
.globl SEGMENT_0
SEGMENT_0: .8byte 2

.globl SEGMENT_1
SEGMENT_1: .8byte 3

.globl SEGMENT_2
SEGMENT_2: .8byte 12
