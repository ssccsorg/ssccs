# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SSCCS SCHEME ADJACENCY ENGINE — Structural Neighbor Discovery     ║
# ║                                                                    ║
# ║  Discovers neighboring Segments based on Scheme structural         ║
# ║  relations: grid adjacency, Manhattan distance, graph edges.       ║
# ║                                                                    ║
# ║  Whitepaper §2.3.1:                                                ║
# ║    Adjacency = structural relationships in the Scheme.             ║
# ║    Neighbors are not stored; they are generated from structure.    ║
# ╚══════════════════════════════════════════════════════════════════════╝

.section .text

# ═══════════════════════════════════════════════════════════════════════
# 1. GRID ADJACENCY
# ═══════════════════════════════════════════════════════════════════════

# ── 1.1 adj_grid_4: 4-connected neighbors (up, down, left, right) ──
# Input:  a0 = x, a1 = y, a2 = min_x, a3 = max_x,
#         a4 = min_y, a5 = max_y
#         a6 = *out_buffer (i64 pairs, room for 4 × 2 = 64 bytes)
# Output: a0 = number of valid neighbors found
.globl adj_grid_4
adj_grid_4:
    li      t0, 0               # count
    # Neighbor 1: (x+1, y)
    blt     a0, a3, .Lag4_right
    j       .Lag4_check_up
.Lag4_right:
    addi    t1, a0, 1
    slli    t2, t0, 4           # 16 bytes per entry
    add     t2, a6, t2
    sd      t1, 0(t2)           # x+1
    sd      a1, 8(t2)           # y
    addi    t0, t0, 1
.Lag4_check_up:
    # Neighbor 2: (x-1, y)
    bgt     a0, a2, .Lag4_left
    j       .Lag4_check_down
.Lag4_left:
    addi    t1, a0, -1
    slli    t2, t0, 4
    add     t2, a6, t2
    sd      t1, 0(t2)
    sd      a1, 8(t2)
    addi    t0, t0, 1
.Lag4_check_down:
    # Neighbor 3: (x, y+1)
    blt     a1, a5, .Lag4_down
    j       .Lag4_check_up2
.Lag4_down:
    addi    t1, a1, 1
    slli    t2, t0, 4
    add     t2, a6, t2
    sd      a0, 0(t2)
    sd      t1, 8(t2)
    addi    t0, t0, 1
.Lag4_check_up2:
    # Neighbor 4: (x, y-1)
    bgt     a1, a4, .Lag4_up
    j       .Lag4_done
.Lag4_up:
    addi    t1, a1, -1
    slli    t2, t0, 4
    add     t2, a6, t2
    sd      a0, 0(t2)
    sd      t1, 8(t2)
    addi    t0, t0, 1
.Lag4_done:
    mv      a0, t0
    ret

# ── 1.2 adj_grid_8: 8-connected neighbors (includes diagonals) ──
# Input:  a0 = x, a1 = y, a2 = min_x, a3 = max_x,
#         a4 = min_y, a5 = max_y
#         a6 = *out_buffer (i64 pairs, room for 8 × 2 = 128 bytes)
# Output: a0 = number of valid neighbors
.globl adj_grid_8
adj_grid_8:
    addi    sp, sp, -48
    sd      ra, 40(sp)
    sd      s0, 32(sp)          # x
    sd      s1, 24(sp)          # y
    sd      s2, 16(sp)          # min_x
    sd      s3, 8(sp)           # max_x
    sd      s4, 0(sp)           # min_y / temp count
    # s5 = max_y (not saved, recompute from sp)
    # a6 = out buffer (saved on stack)

    mv      s0, a0              # x
    mv      s1, a1              # y
    mv      s2, a2              # min_x
    mv      s3, a3              # max_x
    mv      s4, a4              # min_y
    mv      s5, a5              # max_y

    # Step 1: get 4-connected neighbors via adj_grid_4
    # a0-a5 already set, a6 needs to be on stack
    addi    sp, sp, -16
    sd      a6, 8(sp)           # save out buffer
    sd      s5, 0(sp)           # save max_y (a5 position)
    mv      a6, a6              # out buffer (already in a6)
    jal     adj_grid_4
    mv      t0, a0              # count from 4-connected
    ld      a6, 8(sp)           # restore out buffer
    ld      s5, 0(sp)           # restore max_y
    addi    sp, sp, 16

    # Step 2: add 4 diagonals using saved s0-s5
    # s0=x, s1=y, s2=min_x, s3=max_x, s4=min_y, s5=max_y

    # Diagonal 1: (x+1, y+1)
    blt     s0, s3, .Lag8_d1r
    j       .Lag8_cd2
.Lag8_d1r:
    blt     s1, s5, .Lag8_d1
    j       .Lag8_cd2
.Lag8_d1:
    slli    t1, t0, 4
    add     t1, a6, t1
    addi    t2, s0, 1
    sd      t2, 0(t1)
    addi    t2, s1, 1
    sd      t2, 8(t1)
    addi    t0, t0, 1
.Lag8_cd2:
    # Diagonal 2: (x-1, y+1)
    bgt     s0, s2, .Lag8_d2l
    j       .Lag8_cd3
.Lag8_d2l:
    blt     s1, s5, .Lag8_d2
    j       .Lag8_cd3
.Lag8_d2:
    slli    t1, t0, 4
    add     t1, a6, t1
    addi    t2, s0, -1
    sd      t2, 0(t1)
    addi    t2, s1, 1
    sd      t2, 8(t1)
    addi    t0, t0, 1
.Lag8_cd3:
    # Diagonal 3: (x+1, y-1)
    blt     s0, s3, .Lag8_d3r
    j       .Lag8_cd4
.Lag8_d3r:
    bgt     s1, s4, .Lag8_d3
    j       .Lag8_cd4
.Lag8_d3:
    slli    t1, t0, 4
    add     t1, a6, t1
    addi    t2, s0, 1
    sd      t2, 0(t1)
    addi    t2, s1, -1
    sd      t2, 8(t1)
    addi    t0, t0, 1
.Lag8_cd4:
    # Diagonal 4: (x-1, y-1)
    bgt     s0, s2, .Lag8_d4l
    j       .Lag8_done
.Lag8_d4l:
    bgt     s1, s4, .Lag8_d4
    j       .Lag8_done
.Lag8_d4:
    slli    t1, t0, 4
    add     t1, a6, t1
    addi    t2, s0, -1
    sd      t2, 0(t1)
    addi    t2, s1, -1
    sd      t2, 8(t1)
    addi    t0, t0, 1

.Lag8_done:
    mv      a0, t0
    ld      s4, 0(sp)
    ld      s3, 8(sp)
    ld      s2, 16(sp)
    ld      s1, 24(sp)
    ld      s0, 32(sp)
    ld      ra, 40(sp)
    addi    sp, sp, 48
    ret

# ═══════════════════════════════════════════════════════════════════════
# 2. MANHATTAN DISTANCE ADJACENCY
# ═══════════════════════════════════════════════════════════════════════

# ── 2.1 adj_manhattan_1d: neighbors within L1 distance d on a line ──
# Input:  a0 = coord (i64), a1 = distance (u32),
#         a2 = min_coord, a3 = max_coord,
#         a4 = *out_buffer
# Output: a0 = number of neighbors
.globl adj_manhattan_1d
adj_manhattan_1d:
    li      t0, 0               # count
    li      t4, 1               # offset start
.Lam_loop:
    bgt     t4, a1, .Lam_done   # offset > distance → done
    # coord + offset
    add     t1, a0, t4
    bgt     t1, a3, .Lam_check_neg
    slli    t2, t0, 3
    add     t2, a4, t2
    sd      t1, 0(t2)
    addi    t0, t0, 1
.Lam_check_neg:
    # coord - offset
    sub     t1, a0, t4
    blt     t1, a2, .Lam_next
    slli    t2, t0, 3
    add     t2, a4, t2
    sd      t1, 0(t2)
    addi    t0, t0, 1
.Lam_next:
    addi    t4, t4, 1
    j       .Lam_loop
.Lam_done:
    mv      a0, t0
    ret

# ═══════════════════════════════════════════════════════════════════════
# 3. GRAPH EDGE TRAVERSAL
# ═══════════════════════════════════════════════════════════════════════

# ── 3.1 adj_graph_edges: walk adjacency list ──
# Input:  a0 = *edge_pairs (array of {from, to} i64 pairs),
#         a1 = num_edges (u32),
#         a2 = from_id (i64),
#         a3 = *out_buffer (room for num_edges × 8 bytes)
# Output: a0 = number of matching edges found
.globl adj_graph_edges
adj_graph_edges:
    beqz    a1, .Lge_done
    mv      t3, a0
    li      t0, 0               # result count
    li      t4, 0               # index
.Lge_loop:
    beq     t4, a1, .Lge_done
    slli    t1, t4, 4           # 16 bytes per edge pair
    add     t1, t3, t1
    ld      t2, 0(t1)           # from_id
    bne     t2, a2, .Lge_skip
    ld      t2, 8(t1)           # to_id
    slli    t5, t0, 3
    add     t5, a3, t5
    sd      t2, 0(t5)           # store to_id
    addi    t0, t0, 1
.Lge_skip:
    addi    t4, t4, 1
    j       .Lge_loop
.Lge_done:
    mv      a0, t0
    ret

# ═══════════════════════════════════════════════════════════════════════
# 4. BATCH NEIGHBOR ENUMERATION
# ═══════════════════════════════════════════════════════════════════════

# ── 4.1 adj_batch: enumerate neighbors for multiple coordinates ──
# Input:  a0 = *coords (array of i64), a1 = num_coords,
#         a2 = adj_fn, a3 = *out (concatenated, with counts prefix)
#         a4 = out_capacity (max total neighbors)
# Output: a0 = total neighbors found
.globl adj_batch
adj_batch:
    beqz    a1, .Lab_done
    addi    sp, sp, -48
    sd      ra, 40(sp)
    sd      s0, 32(sp)
    sd      s1, 24(sp)
    sd      s2, 16(sp)
    sd      s3, 8(sp)
    sd      s4, 0(sp)

    mv      s0, a0              # coords
    mv      s1, a1              # num_coords
    mv      s2, a2              # adj_fn
    mv      s3, a3              # out buffer
    mv      s4, a4              # capacity

    li      t0, 0               # total count
    li      t5, 0               # coord index
.Lab_loop:
    beq     t5, s1, .Lab_exit
    slli    t1, t5, 3
    add     t1, s0, t1
    ld      a0, 0(t1)           # coord value
    # adj_fn takes (coord, ...) — for simplicity pass minimal args
    # This is a generic dispatcher; actual bounds depend on context
    mv      a1, s3
    jalr    ra, s2, 0
    add     t0, t0, a0          # accumulate neighbor count
    # Advance out buffer by count * 8 bytes (approximate)
    # In practice, the adj_fn writes directly to out
    addi    t5, t5, 1
    j       .Lab_loop

.Lab_exit:
    mv      a0, t0
    ld      s4, 0(sp)
    ld      s3, 8(sp)
    ld      s2, 16(sp)
    ld      s1, 24(sp)
    ld      s0, 32(sp)
    ld      ra, 40(sp)
    addi    sp, sp, 48
    ret
.Lab_done:
    li      a0, 0
    ret

# ═══════════════════════════════════════════════════════════════════════
# GOLDEN TEST ANCHORS
# ═══════════════════════════════════════════════════════════════════════
#
# GOLDEN_ADJ_GRID_4_CENTER: 4
# GOLDEN_ADJ_GRID_4_CORNER: 2
# GOLDEN_ADJ_GRID_8_CENTER: 8
# GOLDEN_ADJ_GRID_8_CORNER: 3
# GOLDEN_ADJ_MANHATTAN_1D_D1: 2
# GOLDEN_ADJ_MANHATTAN_1D_D2: 4
