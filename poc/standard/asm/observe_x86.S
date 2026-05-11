# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SSCCS OBSERVATION ENGINE — x86-64 AT&T Assembly + SSE2 SIMD      ║
# ║                                                                    ║
# ║  System V AMD64 ABI:                                              ║
# ║    %rdi = arg1, %rsi = arg2, %rdx = arg3, %rcx = arg4, %r8 = arg5 ║
# ║    %rax = return (i64), %xmm0 = return (float/double)             ║
# ╚══════════════════════════════════════════════════════════════════════╝

.text

# ═══════════════════════════════════════════════════════════════════════
# 1. BRANCHLESS CONSTRAINT CHECKS
# ═══════════════════════════════════════════════════════════════════════

.globl ck_even
ck_even:
    mov    (%rdi), %rax
    andq    $1, %rax
    xorq    $1, %rax
    ret

.globl ck_range_0_10
ck_range_0_10:
    mov    (%rdi), %rax
    xorl    %edx, %edx
    cmpq    $0, %rax
    setge   %dl
    cmpq    $10, %rax
    setle   %al
    andb    %dl, %al
    movzbl  %al, %eax
    ret

.globl ck_gt
ck_gt:
    mov    (%rdi), %rax
    cmpq    %rsi, %rax
    setg    %al
    movzbl  %al, %eax
    ret

# ═══════════════════════════════════════════════════════════════════════
# 2. SSE2 SIMD BATCH (4 coordinates at once)
# ═══════════════════════════════════════════════════════════════════════

.globl ck_range_4way
ck_range_4way:
    movdqu  (%rdi), %xmm0        # 4×i64
    mov    %rsi, %xmm1
    pshufd  $0x44, %xmm1, %xmm1  # broadcast min
    mov    %rdx, %xmm2
    pshufd  $0x44, %xmm2, %xmm2  # broadcast max

    pcmpgtq %xmm0, %xmm1         # min > coord → -1 : 0
    pcmpgtq %xmm2, %xmm0         # coord > max → -1 : 0
    por     %xmm0, %xmm1         # out-of-range ?
    pcmpeqd %xmm0, %xmm0         # all-ones
    pxor    %xmm0, %xmm1         # invert → in-range

    movmskpd %xmm1, %eax         # bitmap
    ret

.globl ck_even_4way
ck_even_4way:
    movdqu  (%rdi), %xmm0
    movdqa  ones(%rip), %xmm1
    pand    %xmm1, %xmm0
    movdqa  zeros(%rip), %xmm2
    pcmpeqq %xmm2, %xmm0
    movmskpd %xmm0, %eax
    ret

.section .rodata
.align 16
ones:  .quad 1, 1
zeros: .quad 0, 0

.text

# ═══════════════════════════════════════════════════════════════════════
# 3. FIELD COMPOSITION
# ═══════════════════════════════════════════════════════════════════════

.globl compose_and
compose_and:
    pushq   %rbx
    pushq   %r12
    pushq   %r13

    mov    %rdi, %rbx
    mov    %rsi, %r12
    mov    %rdx, %r13

    mov    %r13, %rdi
    call    *%rbx
    movl    %eax, %r14d

    mov    %r13, %rdi
    call    *%r12

    andl    %r14d, %eax

    popq    %r13
    popq    %r12
    popq    %rbx
    ret

.globl compose_or
compose_or:
    pushq   %rbx
    pushq   %r12
    pushq   %r13

    mov    %rdi, %rbx
    mov    %rsi, %r12
    mov    %rdx, %r13

    mov    %r13, %rdi
    call    *%rbx
    movl    %eax, %r14d

    mov    %r13, %rdi
    call    *%r12

    orl     %r14d, %eax

    popq    %r13
    popq    %r12
    popq    %rbx
    ret

.globl compose_3way_and
compose_3way_and:
    pushq   %rbx
    pushq   %r12
    pushq   %r13
    pushq   %r14

    mov    %rdi, %rbx
    mov    %rsi, %r12
    mov    %rdx, %r13
    mov    %rcx, %r14

    mov    %r14, %rdi;  call *%rbx;  movl %eax, %r15d
    mov    %r14, %rdi;  call *%r12;  andl %eax, %r15d
    mov    %r14, %rdi;  call *%r13;  andl %r15d, %eax

    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx
    ret

# ═══════════════════════════════════════════════════════════════════════
# 4. PROJECTORS
# ═══════════════════════════════════════════════════════════════════════

.globl proj_id;  proj_id:  mov (%rdi), %rax;  ret

.globl proj_sum2d
proj_sum2d:
    mov    (%rdi), %rax
    addq    8(%rdi), %rax
    ret

.globl proj_sum3d
proj_sum3d:
    mov    (%rdi), %rax
    addq    8(%rdi), %rax
    addq    16(%rdi), %rax
    ret

.globl proj_parity
proj_parity:
    mov    (%rdi), %rax
    andq    $1, %rax
    ret

# ═══════════════════════════════════════════════════════════════════════
# 5. OBSERVATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════

.globl observe
observe:
    pushq   %r12
    pushq   %r13
    pushq   %r14

    mov    %rdi, %r12          # field_fn
    mov    %rsi, %r13          # coord
    mov    %rdx, %r14          # proj_fn

    mov    %r13, %rdi
    call    *%r12
    testl   %eax, %eax
    jz      .Lobs_reject

    mov    %r13, %rdi
    call    *%r14
    jmp     .Lobs_done

.Lobs_reject:
    movabsq $0x8000000000000000, %rax

.Lobs_done:
    popq    %r14
    popq    %r13
    popq    %r12
    ret

# ═══════════════════════════════════════════════════════════════════════
# 6. BATCH OBSERVATION
# ═══════════════════════════════════════════════════════════════════════

.globl observe_batch
observe_batch:
    testq   %rdx, %rdx
    jz      .Lbatch_exit
    pushq   %r12; pushq %r13; pushq %r14; pushq %r15; pushq %rbx

    mov    %rdi, %r12
    mov    %rsi, %r13
    mov    %rdx, %r14
    mov    %rcx, %r15
    mov    %r8, %rbx

    xorq    %r10, %r10
.Lbatch_loop:
    cmpq    %r14, %r10
    jge     .Lbatch_exit

    mov    (%r13, %r10, 8), %rdi
    mov    %rdi, %r11

    call    *%r12
    testl   %eax, %eax
    jz      .Lbatch_skip

    mov    %r11, %rdi
    call    *%r15
    jmp     .Lbatch_store

.Lbatch_skip:
    movabsq $0x8000000000000000, %rax

.Lbatch_store:
    mov    %rax, (%rbx, %r10, 8)
    incq    %r10
    jmp     .Lbatch_loop

.Lbatch_exit:
    popq    %rbx; popq %r15; popq %r14; popq %r13; popq %r12
    ret

# ═══════════════════════════════════════════════════════════════════════
# 7. STATIC SEGMENTS
# ═══════════════════════════════════════════════════════════════════════

.section .rodata
.align 16

.globl SEG_0;  SEG_0:  .quad 2
.globl SEG_1;  SEG_1:  .quad 3
.globl SEG_2;  SEG_2:  .quad 5
.globl SEG_3;  SEG_3:  .quad 10
.globl SEG_4;  SEG_4:  .quad 12

.globl SEG_4WAY
.align 16
SEG_4WAY: .quad 2, 4, 11, 8

.globl BATCH_TABLE
BATCH_TABLE: .quad SEG_0, SEG_1, SEG_2, SEG_3, SEG_4

.globl NARROW_RESULTS; NARROW_RESULTS: .quad 0,0,0,0,0
.globl BROAD_RESULTS;  BROAD_RESULTS:  .quad 0,0,0,0,0
