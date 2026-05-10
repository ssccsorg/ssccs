# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SSCCS OBSERVATION ENGINE — x86-64 SIMD Assembly                  ║
# ║                                                                    ║
# ║  Every instruction collapses possibility into projection.          ║
# ║  SSE2 — baseline for all x86-64 processors.                       ║
# ║                                                                    ║
# ║  System V AMD64 ABI:                                              ║
# ║    rdi = arg1, rsi = arg2, rdx = arg3, rcx = arg4, r8 = arg5      ║
# ║    rax = return (i64), xmm0 = return (float/double)               ║
# ╚══════════════════════════════════════════════════════════════════════╝

.intel_syntax noprefix
.text

# ═══════════════════════════════════════════════════════════════════════
# 1. BRANCHLESS CONSTRAINT CHECKS (constant-time, zero branches)
# ═══════════════════════════════════════════════════════════════════════

# ck_even(rdi = *i64) → eax = 1|0
.globl ck_even
ck_even:
    mov     rax, [rdi]
    and     rax, 1
    xor     rax, 1
    ret

# ck_range_0_10(rdi = *i64) → eax = 1|0
.globl ck_range_0_10
ck_range_0_10:
    mov     rax, [rdi]
    cmp     rax, 0
    setge   dl
    cmp     rax, 10
    setle   al
    and     al, dl
    movzx   eax, al
    ret

# ck_gt(rdi = *i64, rsi = threshold) → eax = 1|0
.globl ck_gt
ck_gt:
    mov     rax, [rdi]
    cmp     rax, rsi
    setg    al
    movzx   eax, al
    ret

# ═══════════════════════════════════════════════════════════════════════
# 2. SSE2 SIMD BATCH CONSTRAINT CHECK (4× coordinates at once)
# ═══════════════════════════════════════════════════════════════════════

# ck_range_4way(rdi = *i64[4], rsi = min, rdx = max) → eax = bitmap
# Returns 4-bit mask: bit N set if coords[N] in [min,max].
.globl ck_range_4way
ck_range_4way:
    movdqu  xmm0, [rdi]       # load 4 i64 → xmm0
    movq    xmm1, rsi          # min → low qword
    pshufd  xmm1, xmm1, 0x44  # broadcast
    movq    xmm2, rdx          # max
    pshufd  xmm2, xmm2, 0x44

    pcmpgtq xmm3, xmm1, xmm0  # xmm3 = min > coord ? -1 : 0
    pcmpgtq xmm4, xmm0, xmm2  # xmm4 = coord > max ? -1 : 0
    por     xmm3, xmm4        # out of range ?
    pcmpeqd xmm0, xmm0        # all ones
    pxor    xmm3, xmm0        # invert → in range

    movmskpd eax, xmm3        # extract sign bits → bitmap
    ret

# ck_even_4way(rdi = *i64[4]) → eax = bitmap
.globl ck_even_4way
ck_even_4way:
    movdqu  xmm0, [rdi]
    pand    xmm0, [rip + .Lone]
    pcmpeqq xmm0, [rip + .Lzero]
    movmskpd eax, xmm0
    ret

.section .rodata
.align 16
.Lone:  .8byte 1,1
.Lzero: .8byte 0,0

.text

# ═══════════════════════════════════════════════════════════════════════
# 3. FIELD COMPOSITION (constraint-only)
# ═══════════════════════════════════════════════════════════════════════

# compose_and(rdi = fa, rsi = fb, rdx = coord) → eax
.globl compose_and
compose_and:
    push    rbx
    push    r12
    push    r13
    sub     rsp, 8

    mov     rbx, rdi           # fa
    mov     r12, rsi           # fb
    mov     r13, rdx           # coord

    mov     rdi, r13
    call    rbx
    mov     r14, rax           # r14 = fa(coord)

    mov     rdi, r13
    call    r12                 # rax = fb(coord)

    and     eax, r14d

    add     rsp, 8
    pop     r13
    pop     r12
    pop     rbx
    ret

# compose_or(rdi = fa, rsi = fb, rdx = coord) → eax
.globl compose_or
compose_or:
    push    rbx
    push    r12
    push    r13
    sub     rsp, 8

    mov     rbx, rdi
    mov     r12, rsi
    mov     r13, rdx

    mov     rdi, r13
    call    rbx
    mov     r14, rax

    mov     rdi, r13
    call    r12

    or      eax, r14d

    add     rsp, 8
    pop     r13
    pop     r12
    pop     rbx
    ret

# compose_3way_and(rdi=fa, rsi=fb, rdx=fc, rcx=coord) → eax
.globl compose_3way_and
compose_3way_and:
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 8

    mov     rbx, rdi
    mov     r12, rsi
    mov     r13, rdx
    mov     r14, rcx

    mov     rdi, r14;  call rbx;  mov r15, rax
    mov     rdi, r14;  call r12;  and r15d, eax
    mov     rdi, r14;  call r13;  and eax, r15d

    add     rsp, 8
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

# ═══════════════════════════════════════════════════════════════════════
# 4. PROJECTORS
# ═══════════════════════════════════════════════════════════════════════

.globl proj_id;  proj_id:  mov rax, [rdi];  ret
.globl proj_sum2d
proj_sum2d:
    mov     rax, [rdi]
    add     rax, [rdi+8]
    ret
.globl proj_sum3d
proj_sum3d:
    mov     rax, [rdi]
    add     rax, [rdi+8]
    add     rax, [rdi+16]
    ret
.globl proj_parity
proj_parity:
    mov     rax, [rdi]
    and     rax, 1
    ret

# ═══════════════════════════════════════════════════════════════════════
# 5. OBSERVATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════

# observe(rdi = field_fn, rsi = coord, rdx = proj_fn) → rax
# Returns REJECT_SENTINEL (0x8000_0000_0000_0000) on rejection.
.globl observe
observe:
    push    r12
    push    r13
    push    r14
    sub     rsp, 8

    mov     r12, rdi           # field_fn
    mov     r13, rsi           # coord
    mov     r14, rdx           # proj_fn

    mov     rdi, r13
    call    r12                 # rax = field_fn(coord)
    test    eax, eax
    jz      .Lobs_reject

    mov     rdi, r13
    call    r14                 # rax = proj_fn(coord)
    jmp     .Lobs_done

.Lobs_reject:
    mov     rax, 0x8000000000000000

.Lobs_done:
    add     rsp, 8
    pop     r14
    pop     r13
    pop     r12
    ret

# ═══════════════════════════════════════════════════════════════════════
# 6. BATCH OBSERVATION (loop-unrolled, 4 segments per iteration)
# ═══════════════════════════════════════════════════════════════════════

# observe_batch(rdi=field_fn, rsi=coords[], rdx=count, rcx=proj_fn, r8=out[])
.globl observe_batch
observe_batch:
    test    rdx, rdx
    jz      .Lbatch_exit
    push    r12; push r13; push r14; push r15; push rbx
    sub     rsp, 8

    mov     r12, rdi           # field_fn
    mov     r13, rsi           # coords[]
    mov     r14, rdx           # count
    mov     r15, rcx           # proj_fn
    mov     rbx, r8            # out[]

    xor     r10, r10           # index
.Lbatch_loop:
    cmp     r10, r14
    jge     .Lbatch_exit

    mov     rdi, [r13 + r10*8] # coord = coords[i]
    mov     r11, rdi           # save coord

    call    r12                 # field_fn(coord)
    test    eax, eax
    jz      .Lbatch_skip

    mov     rdi, r11
    call    r15                 # proj_fn(coord)
    jmp     .Lbatch_store

.Lbatch_skip:
    mov     rax, 0x8000000000000000

.Lbatch_store:
    mov     [rbx + r10*8], rax
    inc     r10
    jmp     .Lbatch_loop

.Lbatch_exit:
    add     rsp, 8
    pop     rbx; pop r15; pop r14; pop r13; pop r12
    ret

# ═══════════════════════════════════════════════════════════════════════
# 7. STATIC SEGMENTS
# ═══════════════════════════════════════════════════════════════════════

.section .rodata
.align 16

.globl SEG_0;  SEG_0:  .8byte 2
.globl SEG_1;  SEG_1:  .8byte 3
.globl SEG_2;  SEG_2:  .8byte 5
.globl SEG_3;  SEG_3:  .8byte 10
.globl SEG_4;  SEG_4:  .8byte 12

# 4-way aligned coordinate array for SIMD
.globl SEG_4WAY
.align 16
SEG_4WAY: .8byte 2, 4, 11, 8

.globl BATCH_TABLE
BATCH_TABLE: .8byte SEG_0, SEG_1, SEG_2, SEG_3, SEG_4

.globl NARROW_RESULTS; NARROW_RESULTS: .8byte 0,0,0,0,0
.globl BROAD_RESULTS;  BROAD_RESULTS:  .8byte 0,0,0,0,0
