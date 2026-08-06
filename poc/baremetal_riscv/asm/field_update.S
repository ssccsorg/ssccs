# SSCCS Field Update Engine — Constraint & Transition Mutation
#
# Field is the mutable substrate: constraints and transition rules.
# These primitives allow runtime modification of field state.
# Implements custom1/2 opcode (funct3=010).
#
# Whitepaper §2.2:
#   Field is mutable, Segment is immutable.
#   Constraints filter observations; transitions define topology.

.section .text

# Section 1: Constraint Primitives (Field mutation)

# 1.1 field_add_constraint: add a constraint to a field
# Input:  a0 = *field_state (Field descriptor pointer)
#         a1 = *constraint_fn (function pointer)
#         a2 = constraint_id (u32 identifier)
# Output: a0 = 0 on success, -1 on failure (full)
# Field state layout (expected by these primitives):
#   offset 0:   constraint_fn_ptrs[8] (array of function pointers)
#   offset 64:  constraint_ids[8] (array of u32, 8 × 4 = 32 bytes)
#   offset 96:  transition_pairs[16] (array of {from,to,weight}, 16 × 24 = 384 bytes)
#   offset 480: num_constraints (u32 at byte offset 480)
#   offset 484: num_transitions (u32 at byte offset 484)
# Total: ~512 bytes
.globl field_add_constraint
field_add_constraint:
    lw      t0, 480(a0)         # num_constraints
    li      t1, 8               # max constraints
    bge     t0, t1, .Lfac_full
    slli    t2, t0, 3           # offset in fn ptr array (8 bytes each)
    add     t2, a0, t2
    sd      a1, 0(t2)           # store constraint_fn
    # Store constraint_id at offset 64 + idx*4
    li      t2, 64
    add     t2, a0, t2
    slli    t3, t0, 2
    add     t2, t2, t3
    sw      a2, 0(t2)           # store constraint_id
    addi    t0, t0, 1
    sw      t0, 480(a0)         # update count
    li      a0, 0
    ret
.Lfac_full:
    li      a0, -1
    ret

# 1.2 field_remove_constraint: remove by constraint_id
# Input:  a0 = *field_state, a1 = constraint_id
# Output: a0 = 0 on success (or already absent)
.globl field_remove_constraint
field_remove_constraint:
    lw      t0, 480(a0)         # num_constraints
    li      t4, 0               # index
.Lfrc_loop:
    beq     t4, t0, .Lfrc_not_found
    li      t2, 64
    add     t2, a0, t2
    slli    t3, t4, 2
    add     t2, t2, t3
    lw      t3, 0(t2)
    beq     t3, a1, .Lfrc_found
    addi    t4, t4, 1
    j       .Lfrc_loop
.Lfrc_found:
    # Shift remaining entries left
    addi    t5, t4, 1
.Lfrc_shift:
    beq     t5, t0, .Lfrc_done_shift
    slli    t2, t5, 3
    add     t2, a0, t2
    ld      t3, 0(t2)
    slli    t6, t4, 3
    add     t6, a0, t6
    sd      t3, 0(t6)           # move fn ptr
    li      t2, 64
    add     t2, a0, t2
    slli    t3, t5, 2
    add     t2, t2, t3
    lw      t3, 0(t2)
    li      t6, 64
    add     t6, a0, t6
    slli    t1, t4, 2
    add     t6, t6, t1
    sw      t3, 0(t6)           # move id
    addi    t4, t4, 1
    addi    t5, t5, 1
    j       .Lfrc_shift
.Lfrc_done_shift:
    addi    t0, t0, -1
    sw      t0, 480(a0)
    li      a0, 0
    ret
.Lfrc_not_found:
    li      a0, 0               # already absent
    ret

# 1.3 field_clear: reset field to empty
# Input: a0 = *field_state
.globl field_clear
field_clear:
    sw      zero, 480(a0)
    sw      zero, 484(a0)
    ret

# Section 2: Transition Primitives

# 2.1 field_add_transition: add {from, to, weight}
# Input:  a0 = *field_state, a1 = from_id, a2 = to_id,
#         a3 = weight_as_i64 (fixed-point)
# Output: a0 = 0 on success, -1 on failure
.globl field_add_transition
field_add_transition:
    lw      t0, 484(a0)         # num_transitions
    li      t1, 16              # max transitions
    bge     t0, t1, .Lfat_full
    # Transition entry: 24 bytes = 8(from) + 8(to) + 8(weight)
    li      t2, 96              # transition array offset
    add     t2, a0, t2
    li      t3, 24
    mul     t3, t0, t3
    add     t2, t2, t3
    sd      a1, 0(t2)           # from_id
    sd      a2, 8(t2)           # to_id
    sd      a3, 16(t2)          # weight
    addi    t0, t0, 1
    sw      t0, 484(a0)
    li      a0, 0
    ret
.Lfat_full:
    li      a0, -1
    ret

# 2.2 field_update_weight: update weight for transition
# Input:  a0 = *field_state, a1 = from_id, a2 = to_id,
#         a3 = new_weight
# Output: a0 = 0 on success, -1 if not found
.globl field_update_weight
field_update_weight:
    lw      t0, 484(a0)
    li      t4, 0
    li      t2, 96
    add     t2, a0, t2
.Lfuw_loop:
    beq     t4, t0, .Lfuw_not_found
    li      t3, 24
    mul     t3, t4, t3
    add     t5, t2, t3
    ld      t6, 0(t5)           # from_id
    bne     t6, a1, .Lfuw_next
    ld      t6, 8(t5)           # to_id
    bne     t6, a2, .Lfuw_next
    sd      a3, 16(t5)          # update weight
    li      a0, 0
    ret
.Lfuw_next:
    addi    t4, t4, 1
    j       .Lfuw_loop
.Lfuw_not_found:
    li      a0, -1
    ret

# Section 3: Field Query

# 3.1 field_get_transitions: get transitions from a segment
# Input:  a0 = *field_state, a1 = from_id,
#         a2 = *out_buffer (at least 16 × 16 = 256 bytes)
# Output: a0 = number of transitions found
.globl field_get_transitions
field_get_transitions:
    lw      t0, 484(a0)
    li      t4, 0               # output index
    li      t5, 0               # scan index
    li      t2, 96
    add     t2, a0, t2
.Lfgt_loop:
    beq     t5, t0, .Lfgt_done
    li      t3, 24
    mul     t3, t5, t3
    add     t6, t2, t3
    ld      t3, 0(t6)           # from_id
    bne     t3, a1, .Lfgt_next
    # Copy to out buffer: 16 bytes per entry (to_id + weight)
    ld      t3, 8(t6)
    slli    t1, t4, 4
    add     t1, a2, t1
    sd      t3, 0(t1)           # to_id
    ld      t3, 16(t6)
    sd      t3, 8(t1)           # weight
    addi    t4, t4, 1
.Lfgt_next:
    addi    t5, t5, 1
    j       .Lfgt_loop
.Lfgt_done:
    mv      a0, t4
    ret

# GOLDEN TEST ANCHORS
#
# GOLDEN_FIELD_ADD_CONSTRAINT: 0
# GOLDEN_FIELD_REMOVE_CONSTRAINT: 0
# GOLDEN_FIELD_ADD_TRANSITION: 0
# GOLDEN_FIELD_UPDATE_WEIGHT: 0
