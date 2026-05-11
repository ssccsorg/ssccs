# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SSCCS SCHEME LAYOUT ENGINE — Coordinate-to-Address Mapping        ║
# ║                                                                    ║
# ║  Maps abstract Scheme coordinates to logical addresses using       ║
# ║  various layout strategies (Linear, RowMajor, ColumnMajor, ZOrder).║
# ║                                                                    ║
# ║  Whitepaper §4.1:                                                  ║
# ║    Memory layout = structural locality → spatial locality          ║
# ║    Cache-line-aligned segments preserve relational topology.       ║
# ╚══════════════════════════════════════════════════════════════════════╝

.section .text

# ═══════════════════════════════════════════════════════════════════════
# 1. LINEAR LAYOUT
# ═══════════════════════════════════════════════════════════════════════

# ── 1.1 layout_linear_1d: offset = coord × stride ──
# Input:  a0 = coord (i64), a1 = stride (i64)
# Output: a0 = byte offset
.globl layout_linear_1d
layout_linear_1d:
    mul     a0, a0, a1
    ret

# ── 1.2 layout_linear_nd: offset = Σ (coord_i × stride_i) ──
# Input:  a0 = *coords (i64 array), a1 = *strides (i64 array),
#         a2 = dimensions (u32)
# Output: a0 = byte offset
.globl layout_linear_nd
layout_linear_nd:
    beqz    a2, .Lln_zero
    mv      t3, a0
    mv      t4, a1
    li      t0, 0               # accumulator
    li      t5, 0               # index
.Lln_loop:
    beq     t5, a2, .Lln_done
    slli    t1, t5, 3
    add     t2, t3, t1;  ld t2, 0(t2)   # coord_i
    add     t1, t4, t1;  ld t1, 0(t1)   # stride_i
    mul     t2, t2, t1                   # coord_i × stride_i
    add     t0, t0, t2
    addi    t5, t5, 1
    j       .Lln_loop
.Lln_done:
    mv      a0, t0
    ret
.Lln_zero:
    li      a0, 0
    ret

# ═══════════════════════════════════════════════════════════════════════
# 2. ROW-MAJOR LAYOUT (2D)
# ═══════════════════════════════════════════════════════════════════════

# ── 2.1 layout_row_major_2d: offset = (y × width + x) × elem_size ──
# Input:  a0 = x, a1 = y, a2 = width, a3 = elem_size
# Output: a0 = byte offset
.globl layout_row_major_2d
layout_row_major_2d:
    mul     t0, a1, a2          # y × width
    add     t0, t0, a0          # + x
    mul     a0, t0, a3          # × elem_size
    ret

# ── 2.2 layout_row_major_3d: offset = ((z × height + y) × width + x) × elem_size ──
# Input:  a0 = x, a1 = y, a2 = z, a3 = width, a4 = height,
#         a5 = elem_size
# Output: a0 = byte offset
.globl layout_row_major_3d
layout_row_major_3d:
    mul     t0, a2, a4          # z × height
    add     t0, t0, a1          # + y
    mul     t0, t0, a3          # × width
    add     t0, t0, a0          # + x
    mul     a0, t0, a5          # × elem_size
    ret

# ═══════════════════════════════════════════════════════════════════════
# 3. COLUMN-MAJOR LAYOUT (2D)
# ═══════════════════════════════════════════════════════════════════════

# ── 3.1 layout_col_major_2d: offset = (x × height + y) × elem_size ──
# Input:  a0 = x, a1 = y, a2 = height, a3 = elem_size
# Output: a0 = byte offset
.globl layout_col_major_2d
layout_col_major_2d:
    mul     t0, a0, a2          # x × height
    add     t0, t0, a1          # + y
    mul     a0, t0, a3          # × elem_size
    ret

# ═══════════════════════════════════════════════════════════════════════
# 4. Z-ORDER (MORTON) LAYOUT
# ═══════════════════════════════════════════════════════════════════════

# ── 4.1 Helper: interleave bits (x, y → morton) ──
# Part 1 of 2: spread lower 16 bits of a0 to every other bit
# Internal helper, not globally exposed
# ── 4.2 morton_encode_2d: Z-order for 2D ──
# Input:  a0 = x (i64), a1 = y (i64)
# Output: a0 = morton code
.globl morton_encode_2d
morton_encode_2d:
    # Simple bit interleaving for 32-bit coordinates
    # Using the classic spread-and-shift method

    # Spread x: (x | (x << 8)) & 0x00FF00FF, etc.
    mv      t0, a0
    mv      t1, a1

    # Spread lower 16 bits of t0
    li      t2, 0x0000FFFF
    and     t0, t0, t2
    and     t1, t1, t2

    # Stage 1: spread 16→32
    li      t2, 0x00FF00FF
    or      t3, t0, t0
    slli    t3, t0, 8
    or      t0, t0, t3
    and     t0, t0, t2
    or      t3, t1, t1
    slli    t3, t1, 8
    or      t1, t1, t3
    and     t1, t1, t2

    # Stage 2: spread 8→16
    li      t2, 0x0F0F0F0F
    slli    t3, t0, 4
    or      t0, t0, t3
    and     t0, t0, t2
    slli    t3, t1, 4
    or      t1, t1, t3
    and     t1, t1, t2

    # Stage 3: spread 4→8
    li      t2, 0x33333333
    slli    t3, t0, 2
    or      t0, t0, t3
    and     t0, t0, t2
    slli    t3, t1, 2
    or      t1, t1, t3
    and     t1, t1, t2

    # Stage 4: spread 2→4
    li      t2, 0x55555555
    slli    t3, t0, 1
    or      t0, t0, t3
    and     t0, t0, t2
    slli    t3, t1, 1
    or      t1, t1, t3
    and     t1, t1, t2

    # Interleave: (x bits) | (y bits << 1)
    slli    t1, t1, 1
    or      a0, t0, t1
    ret

# ── 4.3 layout_zorder_2d: offset = morton(x,y) × elem_size ──
# Input:  a0 = x, a1 = y, a2 = elem_size
# Output: a0 = byte offset
.globl layout_zorder_2d
layout_zorder_2d:
    addi    sp, sp, -16
    sd      ra, 8(sp)
    sd      a2, 0(sp)
    jal     morton_encode_2d    # a0 = morton code
    ld      t0, 0(sp)
    mul     a0, a0, t0          # × elem_size
    ld      ra, 8(sp)
    addi    sp, sp, 16
    ret

# ═══════════════════════════════════════════════════════════════════════
# 5. BATCH ADDRESS TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

# ── 5.1 layout_batch: translate array of coordinate sets ──
# Input:  a0 = *coord_sets (array of pointers to coord arrays)
#         a1 = *strides (or dims descriptor)
#         a2 = count (number of coord sets)
#         a3 = layout_fn (function pointer)
#         a4 = *out (array of offsets)
.globl layout_batch
layout_batch:
    beqz    a2, .Llb_done
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
.Llb_loop:
    beq     t0, s2, .Llb_exit
    slli    t1, t0, 3
    add     t2, s0, t1;  ld a0, 0(t2)   # coord_ptr
    # Pass strides as a1 (or descriptor)
    mv      a1, s1
    jalr    ra, s3, 0                    # offset = layout_fn(coord, strides)

    slli    t1, t0, 3
    add     t2, s4, t1;  sd a0, 0(t2)   # out[i] = offset

    addi    t0, t0, 1
    j       .Llb_loop

.Llb_exit:
    ld      s4, 0(sp)
    ld      s3, 8(sp)
    ld      s2, 16(sp)
    ld      s1, 24(sp)
    ld      s0, 32(sp)
    ld      ra, 40(sp)
    addi    sp, sp, 48
    ret
.Llb_done:
    ret

# ═══════════════════════════════════════════════════════════════════════
# GOLDEN TEST ANCHORS
# ═══════════════════════════════════════════════════════════════════════
#
# GOLDEN_LAYOUT_LINEAR_1D: 42
# GOLDEN_LAYOUT_ROW_MAJOR_2D: 42
# GOLDEN_LAYOUT_COL_MAJOR_2D: 34
# GOLDEN_MORTON_2D: 9
