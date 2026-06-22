# Godbolt 汇编解读记录

本文档用于记录 `godbolt.org` 上对 Lab01 各个核心函数的汇编分析结果。建议每完成一组对比，就把截图、编译选项和结论补充到对应小节中，后续可以直接整理进实验报告。

## 通用设置

- 编译器：`x86-64 gcc`
- 语法：`Intel syntax`
- 建议开启：
  - `Demangle identifiers`
  - `Filter library code`
- 建议测试的编译选项：
  - `-O0 -std=c++17`
  - `-O2 -std=c++17`
  - `-O3 -std=c++17`
  - `-O3 -march=native -std=c++17`

---

## 一、矩阵组

### 1. `col_naive` vs `row_cache`

#### 样例文件

- `matrix/col_naive.cpp`
- `matrix/row_cache.cpp`

#### 建议截图

- `-O0` 下两者核心循环各一张
- `-O3` 下两者核心循环各一张
- 如果 `-O3 -march=native` 出现明显 SIMD，再补一张

#### 汇编粘贴区

`col_naive @ -O0`
```asm
idx(unsigned long, unsigned long):
        push    rbp
        mov     rbp, rsp
        mov     QWORD PTR [rbp-8], rdi
        mov     QWORD PTR [rbp-16], rsi
        mov     rax, QWORD PTR [rbp-8]
        sal     rax, 10
        mov     rdx, rax
        mov     rax, QWORD PTR [rbp-16]
        add     rax, rdx
        pop     rbp
        ret
init_data():
        push    rbp
        mov     rbp, rsp
        sub     rsp, 24
        mov     QWORD PTR [rbp-8], 0
        jmp     .L4
.L11:
        mov     rcx, QWORD PTR [rbp-8]
        movabs  rdx, 5895351198814392785
        mov     rax, rcx
        mul     rdx
        mov     rax, rcx
        sub     rax, rdx
        shr     rax
        add     rax, rdx
        shr     rax, 6
        imul    rdx, rax, 97
        mov     rax, rcx
        sub     rax, rdx
        add     rax, 1
        test    rax, rax
        js      .L5
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rax
        jmp     .L6
.L5:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
.L6:
        movsd   xmm1, QWORD PTR .LC0[rip]
        mulsd   xmm0, xmm1
        mov     rax, QWORD PTR [rbp-8]
        movsd   QWORD PTR g_vec[0+rax*8], xmm0
        mov     rax, QWORD PTR [rbp-8]
        pxor    xmm0, xmm0
        movsd   QWORD PTR g_out[0+rax*8], xmm0
        mov     QWORD PTR [rbp-16], 0
        jmp     .L7
.L10:
        mov     rdx, QWORD PTR [rbp-8]
        mov     rax, QWORD PTR [rbp-16]
        lea     rcx, [rdx+rax]
        movabs  rdx, -7999030616033345391
        mov     rax, rcx
        mul     rdx
        mov     rax, rdx
        shr     rax, 6
        imul    rdx, rax, 113
        mov     rax, rcx
        sub     rax, rdx
        test    rax, rax
        js      .L8
        pxor    xmm2, xmm2
        cvtsi2sd        xmm2, rax
        movsd   QWORD PTR [rbp-24], xmm2
        jmp     .L9
.L8:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
        movsd   QWORD PTR [rbp-24], xmm0
.L9:
        mov     rdx, QWORD PTR [rbp-16]
        mov     rax, QWORD PTR [rbp-8]
        mov     rsi, rdx
        mov     rdi, rax
        call    idx(unsigned long, unsigned long)
        movsd   xmm3, QWORD PTR [rbp-24]
        movsd   QWORD PTR g_matrix[0+rax*8], xmm3
        add     QWORD PTR [rbp-16], 1
.L7:
        cmp     QWORD PTR [rbp-16], 1023
        jbe     .L10
        add     QWORD PTR [rbp-8], 1
.L4:
        cmp     QWORD PTR [rbp-8], 1023
        jbe     .L11
        nop
        nop
        leave
        ret
col_naive():
        push    rbp
        mov     rbp, rsp
        sub     rsp, 32
        mov     QWORD PTR [rbp-8], 0
        jmp     .L13
.L16:
        pxor    xmm0, xmm0
        movsd   QWORD PTR [rbp-16], xmm0
        mov     QWORD PTR [rbp-24], 0
        jmp     .L14
.L15:
        mov     rdx, QWORD PTR [rbp-8]
        mov     rax, QWORD PTR [rbp-24]
        mov     rsi, rdx
        mov     rdi, rax
        call    idx(unsigned long, unsigned long)
        movsd   xmm1, QWORD PTR g_matrix[0+rax*8]
        mov     rax, QWORD PTR [rbp-24]
        movsd   xmm0, QWORD PTR g_vec[0+rax*8]
        mulsd   xmm0, xmm1
        movsd   xmm1, QWORD PTR [rbp-16]
        addsd   xmm0, xmm1
        movsd   QWORD PTR [rbp-16], xmm0
        add     QWORD PTR [rbp-24], 1
.L14:
        cmp     QWORD PTR [rbp-24], 1023
        jbe     .L15
        mov     rax, QWORD PTR [rbp-8]
        movsd   xmm0, QWORD PTR [rbp-16]
        movsd   QWORD PTR g_out[0+rax*8], xmm0
        add     QWORD PTR [rbp-8], 1
.L13:
        cmp     QWORD PTR [rbp-8], 1023
        jbe     .L16
        nop
        nop
        leave
        ret
main:
        push    rbp
        mov     rbp, rsp
        call    init_data()
        call    col_naive()
        movsd   xmm0, QWORD PTR g_out[rip]
        cvttsd2si       eax, xmm0
        pop     rbp
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache @ -O0`
```asm
idx(unsigned long, unsigned long):
        push    rbp
        mov     rbp, rsp
        mov     QWORD PTR [rbp-8], rdi
        mov     QWORD PTR [rbp-16], rsi
        mov     rax, QWORD PTR [rbp-8]
        sal     rax, 10
        mov     rdx, rax
        mov     rax, QWORD PTR [rbp-16]
        add     rax, rdx
        pop     rbp
        ret
init_data():
        push    rbp
        mov     rbp, rsp
        sub     rsp, 24
        mov     QWORD PTR [rbp-8], 0
        jmp     .L4
.L11:
        mov     rcx, QWORD PTR [rbp-8]
        movabs  rdx, 5895351198814392785
        mov     rax, rcx
        mul     rdx
        mov     rax, rcx
        sub     rax, rdx
        shr     rax
        add     rax, rdx
        shr     rax, 6
        imul    rdx, rax, 97
        mov     rax, rcx
        sub     rax, rdx
        add     rax, 1
        test    rax, rax
        js      .L5
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rax
        jmp     .L6
.L5:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
.L6:
        movsd   xmm1, QWORD PTR .LC0[rip]
        mulsd   xmm0, xmm1
        mov     rax, QWORD PTR [rbp-8]
        movsd   QWORD PTR g_vec[0+rax*8], xmm0
        mov     rax, QWORD PTR [rbp-8]
        pxor    xmm0, xmm0
        movsd   QWORD PTR g_out[0+rax*8], xmm0
        mov     QWORD PTR [rbp-16], 0
        jmp     .L7
.L10:
        mov     rdx, QWORD PTR [rbp-8]
        mov     rax, QWORD PTR [rbp-16]
        lea     rcx, [rdx+rax]
        movabs  rdx, -7999030616033345391
        mov     rax, rcx
        mul     rdx
        mov     rax, rdx
        shr     rax, 6
        imul    rdx, rax, 113
        mov     rax, rcx
        sub     rax, rdx
        test    rax, rax
        js      .L8
        pxor    xmm2, xmm2
        cvtsi2sd        xmm2, rax
        movsd   QWORD PTR [rbp-24], xmm2
        jmp     .L9
.L8:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
        movsd   QWORD PTR [rbp-24], xmm0
.L9:
        mov     rdx, QWORD PTR [rbp-16]
        mov     rax, QWORD PTR [rbp-8]
        mov     rsi, rdx
        mov     rdi, rax
        call    idx(unsigned long, unsigned long)
        movsd   xmm3, QWORD PTR [rbp-24]
        movsd   QWORD PTR g_matrix[0+rax*8], xmm3
        add     QWORD PTR [rbp-16], 1
.L7:
        cmp     QWORD PTR [rbp-16], 1023
        jbe     .L10
        add     QWORD PTR [rbp-8], 1
.L4:
        cmp     QWORD PTR [rbp-8], 1023
        jbe     .L11
        nop
        nop
        leave
        ret
row_cache():
        push    rbp
        mov     rbp, rsp
        mov     QWORD PTR [rbp-8], 0
        jmp     .L13
.L14:
        mov     rax, QWORD PTR [rbp-8]
        pxor    xmm0, xmm0
        movsd   QWORD PTR g_out[0+rax*8], xmm0
        add     QWORD PTR [rbp-8], 1
.L13:
        cmp     QWORD PTR [rbp-8], 1023
        jbe     .L14
        mov     QWORD PTR [rbp-16], 0
        jmp     .L15
.L18:
        mov     rax, QWORD PTR [rbp-16]
        movsd   xmm0, QWORD PTR g_vec[0+rax*8]
        movsd   QWORD PTR [rbp-32], xmm0
        mov     rax, QWORD PTR [rbp-16]
        sal     rax, 10
        mov     QWORD PTR [rbp-40], rax
        mov     QWORD PTR [rbp-24], 0
        jmp     .L16
.L17:
        mov     rax, QWORD PTR [rbp-24]
        movsd   xmm1, QWORD PTR g_out[0+rax*8]
        mov     rdx, QWORD PTR [rbp-40]
        mov     rax, QWORD PTR [rbp-24]
        add     rax, rdx
        movsd   xmm0, QWORD PTR g_matrix[0+rax*8]
        mulsd   xmm0, QWORD PTR [rbp-32]
        addsd   xmm0, xmm1
        mov     rax, QWORD PTR [rbp-24]
        movsd   QWORD PTR g_out[0+rax*8], xmm0
        add     QWORD PTR [rbp-24], 1
.L16:
        cmp     QWORD PTR [rbp-24], 1023
        jbe     .L17
        add     QWORD PTR [rbp-16], 1
.L15:
        cmp     QWORD PTR [rbp-16], 1023
        jbe     .L18
        nop
        nop
        pop     rbp
        ret
main:
        push    rbp
        mov     rbp, rsp
        call    init_data()
        call    row_cache()
        movsd   xmm0, QWORD PTR g_out[rip]
        cvttsd2si       eax, xmm0
        pop     rbp
        ret
.LC0:
        .long   0
        .long   1070596096
```

`col_naive @ -O3`
```asm
init_data():
        movsd   xmm1, QWORD PTR .LC0[rip]
        xor     esi, esi
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rsi
        pxor    xmm0, xmm0
        mul     rcx
        mov     rax, rsi
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rsi
        sub     rdx, rax
        lea     rax, [rdx+1]
        cvtsi2sd        xmm0, rax
        mulsd   xmm0, xmm1
        movsd   QWORD PTR g_vec[0+rsi*8], xmm0
        add     rsi, 1
        cmp     rsi, 1024
        jne     .L2
        mov     edi, OFFSET FLAT:g_out
        mov     rcx, rsi
        xor     eax, eax
        xor     r9d, r9d
        rep stosq
        xor     edi, edi
        movabs  r8, -7999030616033345391
.L4:
        mov     rcx, r9
.L3:
        mov     rax, rcx
        pxor    xmm0, xmm0
        mul     r8
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        cvtsi2sd        xmm0, rax
        movsd   QWORD PTR g_matrix[rdi+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, rsi
        jne     .L3
        add     r9, 1
        add     rdi, 8184
        lea     rsi, [rcx+1]
        cmp     r9, 1024
        jne     .L4
        ret
col_naive():
        xor     esi, esi
.L10:
        lea     rcx, g_matrix[rsi]
        pxor    xmm1, xmm1
        xor     eax, eax
.L11:
        movsd   xmm0, QWORD PTR g_vec[0+rax*8]
        mov     rdx, rax
        add     rax, 1
        sal     rdx, 13
        unpcklpd        xmm0, xmm0
        mulpd   xmm0, XMMWORD PTR [rcx+rdx]
        addpd   xmm1, xmm0
        cmp     rax, 1024
        jne     .L11
        movaps  XMMWORD PTR g_out[rsi], xmm1
        add     rsi, 16
        cmp     rsi, 8192
        jne     .L10
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    col_naive()
        cvttsd2si       eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache @ -O3`
```asm
init_data():
        movsd   xmm1, QWORD PTR .LC0[rip]
        xor     esi, esi
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rsi
        pxor    xmm0, xmm0
        mul     rcx
        mov     rax, rsi
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rsi
        sub     rdx, rax
        lea     rax, [rdx+1]
        cvtsi2sd        xmm0, rax
        mulsd   xmm0, xmm1
        movsd   QWORD PTR g_vec[0+rsi*8], xmm0
        add     rsi, 1
        cmp     rsi, 1024
        jne     .L2
        mov     edi, OFFSET FLAT:g_out
        mov     rcx, rsi
        xor     eax, eax
        xor     r9d, r9d
        rep stosq
        xor     edi, edi
        movabs  r8, -7999030616033345391
.L4:
        mov     rcx, r9
.L3:
        mov     rax, rcx
        pxor    xmm0, xmm0
        mul     r8
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        cvtsi2sd        xmm0, rax
        movsd   QWORD PTR g_matrix[rdi+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, rsi
        jne     .L3
        add     r9, 1
        add     rdi, 8184
        lea     rsi, [rcx+1]
        cmp     r9, 1024
        jne     .L4
        ret
row_cache():
        mov     ecx, 1024
        xor     eax, eax
        mov     edi, OFFSET FLAT:g_out
        xor     esi, esi
        rep stosq
        mov     edx, OFFSET FLAT:g_matrix
.L11:
        movsd   xmm3, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        movsd   xmm2, QWORD PTR g_vec[8+rsi*8]
        unpcklpd        xmm3, xmm3
        unpcklpd        xmm2, xmm2
.L10:
        movapd  xmm0, XMMWORD PTR [rdx+rax]
        mulpd   xmm0, xmm3
        addpd   xmm0, XMMWORD PTR g_out[rax]
        movaps  XMMWORD PTR g_out[rax], xmm0
        movapd  xmm1, XMMWORD PTR [rcx+rax]
        add     rax, 16
        mulpd   xmm1, xmm2
        addpd   xmm0, xmm1
        movaps  XMMWORD PTR g_out[rax-16], xmm0
        cmp     rax, 8192
        jne     .L10
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L11
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache()
        cvttsd2si       eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`col_naive @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm2, QWORD PTR .LC0[rip]
        push    rbx
        vxorps  xmm1, xmm1, xmm1
        xor     ebx, ebx
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rbx
        mul     rcx
        mov     rax, rbx
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rbx
        sub     rdx, rax
        lea     rax, [rdx+1]
        vcvtsi2sd       xmm0, xmm1, rax
        vmulsd  xmm0, xmm0, xmm2
        vmovsd  QWORD PTR g_vec[0+rbx*8], xmm0
        inc     rbx
        cmp     rbx, 1024
        jne     .L2
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     edx, 8192
        call    memset
        xor     esi, esi
        xor     r8d, r8d
        vxorps  xmm1, xmm1, xmm1
        movabs  rdi, -7999030616033345391
.L4:
        mov     rcx, r8
.L3:
        mov     rax, rcx
        mul     rdi
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        vcvtsi2sd       xmm0, xmm1, rax
        vmovlpd QWORD PTR g_matrix[rsi+rcx*8], xmm0
        inc     rcx
        cmp     rcx, rbx
        jne     .L3
        inc     r8
        add     rsi, 8184
        lea     rbx, [rcx+1]
        cmp     r8, 1024
        jne     .L4
        pop     rbx
        ret
col_naive():
        xor     esi, esi
.L11:
        lea     rcx, g_matrix[rsi]
        vxorpd  xmm0, xmm0, xmm0
        xor     eax, eax
.L12:
        vbroadcastsd    ymm1, QWORD PTR g_vec[0+rax*8]
        mov     rdx, rax
        inc     rax
        sal     rdx, 13
        vfmadd231pd     ymm0, ymm1, YMMWORD PTR [rcx+rdx]
        cmp     rax, 1024
        jne     .L12
        vmovapd YMMWORD PTR g_out[rsi], ymm0
        add     rsi, 32
        cmp     rsi, 8192
        jne     .L11
        vzeroupper
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    col_naive()
        vcvttsd2si      eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm2, QWORD PTR .LC0[rip]
        push    rbx
        vxorps  xmm1, xmm1, xmm1
        xor     ebx, ebx
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rbx
        mul     rcx
        mov     rax, rbx
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rbx
        sub     rdx, rax
        lea     rax, [rdx+1]
        vcvtsi2sd       xmm0, xmm1, rax
        vmulsd  xmm0, xmm0, xmm2
        vmovsd  QWORD PTR g_vec[0+rbx*8], xmm0
        inc     rbx
        cmp     rbx, 1024
        jne     .L2
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     edx, 8192
        call    memset
        xor     esi, esi
        xor     r8d, r8d
        vxorps  xmm1, xmm1, xmm1
        movabs  rdi, -7999030616033345391
.L4:
        mov     rcx, r8
.L3:
        mov     rax, rcx
        mul     rdi
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        vcvtsi2sd       xmm0, xmm1, rax
        vmovlpd QWORD PTR g_matrix[rsi+rcx*8], xmm0
        inc     rcx
        cmp     rcx, rbx
        jne     .L3
        inc     r8
        add     rsi, 8184
        lea     rbx, [rcx+1]
        cmp     r8, 1024
        jne     .L4
        pop     rbx
        ret
row_cache():
        push    rbp
        mov     edx, 8192
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     rbp, rsp
        and     rsp, -32
        call    memset
        mov     edx, OFFSET FLAT:g_matrix
        xor     esi, esi
.L12:
        vbroadcastsd    ymm2, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        vbroadcastsd    ymm1, QWORD PTR g_vec[8+rsi*8]
.L11:
        vmovapd ymm0, YMMWORD PTR [rdx+rax]
        vfmadd213pd     ymm0, ymm2, YMMWORD PTR g_out[rax]
        vmovapd YMMWORD PTR g_out[rax], ymm0
        vfmadd231pd     ymm0, ymm1, YMMWORD PTR [rcx+rax]
        add     rax, 32
        vmovapd YMMWORD PTR g_out[rax-32], ymm0
        cmp     rax, 8192
        jne     .L11
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L12
        vzeroupper
        leave
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache()
        vcvttsd2si      eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

#### 重点观察

- `col_naive` 是否存在跨行访存导致的复杂地址计算
- `row_cache` 是否形成更连续的内存访问模式
- 编译器是否对 `row_cache` 更容易做展开或向量化

#### 记录模板

- 编译选项：
- 核心汇编特征：
- 与对照函数相比的差异：
- 对性能结果的解释：

#### 可直接写入报告的结论模板

- `col_naive` 的内层循环围绕按列访问展开，地址步长较大，不利于 cache 行为。
- `row_cache` 的内层循环对应顺序访问连续元素，汇编更紧凑，说明编译器更容易生成高效的访存与乘加序列。

---

### 2. `row_cache` vs `row_cache_unroll4`

#### 样例文件

- `matrix/row_cache.cpp`
- `matrix/row_cache_unroll4.cpp`

#### 建议截图

- `-O3` 下两者核心循环
- `-O3 -march=native` 下两者核心循环

#### 汇编粘贴区

`row_cache @ -O3`
```asm
init_data():
        movsd   xmm1, QWORD PTR .LC0[rip]
        xor     esi, esi
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rsi
        pxor    xmm0, xmm0
        mul     rcx
        mov     rax, rsi
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rsi
        sub     rdx, rax
        lea     rax, [rdx+1]
        cvtsi2sd        xmm0, rax
        mulsd   xmm0, xmm1
        movsd   QWORD PTR g_vec[0+rsi*8], xmm0
        add     rsi, 1
        cmp     rsi, 1024
        jne     .L2
        mov     edi, OFFSET FLAT:g_out
        mov     rcx, rsi
        xor     eax, eax
        xor     r9d, r9d
        rep stosq
        xor     edi, edi
        movabs  r8, -7999030616033345391
.L4:
        mov     rcx, r9
.L3:
        mov     rax, rcx
        pxor    xmm0, xmm0
        mul     r8
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        cvtsi2sd        xmm0, rax
        movsd   QWORD PTR g_matrix[rdi+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, rsi
        jne     .L3
        add     r9, 1
        add     rdi, 8184
        lea     rsi, [rcx+1]
        cmp     r9, 1024
        jne     .L4
        ret
row_cache():
        mov     ecx, 1024
        xor     eax, eax
        mov     edi, OFFSET FLAT:g_out
        xor     esi, esi
        rep stosq
        mov     edx, OFFSET FLAT:g_matrix
.L11:
        movsd   xmm3, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        movsd   xmm2, QWORD PTR g_vec[8+rsi*8]
        unpcklpd        xmm3, xmm3
        unpcklpd        xmm2, xmm2
.L10:
        movapd  xmm0, XMMWORD PTR [rdx+rax]
        mulpd   xmm0, xmm3
        addpd   xmm0, XMMWORD PTR g_out[rax]
        movaps  XMMWORD PTR g_out[rax], xmm0
        movapd  xmm1, XMMWORD PTR [rcx+rax]
        add     rax, 16
        mulpd   xmm1, xmm2
        addpd   xmm0, xmm1
        movaps  XMMWORD PTR g_out[rax-16], xmm0
        cmp     rax, 8192
        jne     .L10
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L11
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache()
        cvttsd2si       eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache_unroll4 @ -O3`
```asm
init_data():
        movsd   xmm1, QWORD PTR .LC0[rip]
        xor     esi, esi
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rsi
        pxor    xmm0, xmm0
        mul     rcx
        mov     rax, rsi
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rsi
        sub     rdx, rax
        lea     rax, [rdx+1]
        cvtsi2sd        xmm0, rax
        mulsd   xmm0, xmm1
        movsd   QWORD PTR g_vec[0+rsi*8], xmm0
        add     rsi, 1
        cmp     rsi, 1024
        jne     .L2
        mov     edi, OFFSET FLAT:g_out
        mov     rcx, rsi
        xor     eax, eax
        xor     r9d, r9d
        rep stosq
        xor     edi, edi
        movabs  r8, -7999030616033345391
.L4:
        mov     rcx, r9
.L3:
        mov     rax, rcx
        pxor    xmm0, xmm0
        mul     r8
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        cvtsi2sd        xmm0, rax
        movsd   QWORD PTR g_matrix[rdi+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, rsi
        jne     .L3
        add     r9, 1
        add     rdi, 8184
        lea     rsi, [rcx+1]
        cmp     r9, 1024
        jne     .L4
        ret
row_cache_unroll4():
        mov     ecx, 1024
        xor     eax, eax
        mov     edi, OFFSET FLAT:g_out
        xor     esi, esi
        rep stosq
        mov     edx, OFFSET FLAT:g_matrix
.L11:
        movsd   xmm4, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        movsd   xmm3, QWORD PTR g_vec[8+rsi*8]
        unpcklpd        xmm4, xmm4
        unpcklpd        xmm3, xmm3
.L10:
        movapd  xmm0, XMMWORD PTR [rdx+rax]
        movapd  xmm1, XMMWORD PTR [rdx+16+rax]
        mulpd   xmm0, xmm4
        mulpd   xmm1, xmm4
        addpd   xmm0, XMMWORD PTR g_out[rax]
        addpd   xmm1, XMMWORD PTR g_out[rax+16]
        movaps  XMMWORD PTR g_out[rax], xmm0
        movaps  XMMWORD PTR g_out[rax+16], xmm1
        movapd  xmm2, XMMWORD PTR [rcx+16+rax]
        mulpd   xmm2, xmm3
        addpd   xmm1, xmm2
        movapd  xmm2, XMMWORD PTR [rcx+rax]
        add     rax, 32
        mulpd   xmm2, xmm3
        movaps  XMMWORD PTR g_out[rax-16], xmm1
        addpd   xmm0, xmm2
        movaps  XMMWORD PTR g_out[rax-32], xmm0
        cmp     rax, 8192
        jne     .L10
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L11
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache_unroll4()
        cvttsd2si       eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm2, QWORD PTR .LC0[rip]
        push    rbx
        vxorps  xmm1, xmm1, xmm1
        xor     ebx, ebx
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rbx
        mul     rcx
        mov     rax, rbx
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rbx
        sub     rdx, rax
        lea     rax, [rdx+1]
        vcvtsi2sd       xmm0, xmm1, rax
        vmulsd  xmm0, xmm0, xmm2
        vmovsd  QWORD PTR g_vec[0+rbx*8], xmm0
        inc     rbx
        cmp     rbx, 1024
        jne     .L2
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     edx, 8192
        call    memset
        xor     esi, esi
        xor     r8d, r8d
        vxorps  xmm1, xmm1, xmm1
        movabs  rdi, -7999030616033345391
.L4:
        mov     rcx, r8
.L3:
        mov     rax, rcx
        mul     rdi
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        vcvtsi2sd       xmm0, xmm1, rax
        vmovlpd QWORD PTR g_matrix[rsi+rcx*8], xmm0
        inc     rcx
        cmp     rcx, rbx
        jne     .L3
        inc     r8
        add     rsi, 8184
        lea     rbx, [rcx+1]
        cmp     r8, 1024
        jne     .L4
        pop     rbx
        ret
row_cache():
        push    rbp
        mov     edx, 8192
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     rbp, rsp
        and     rsp, -32
        call    memset
        mov     edx, OFFSET FLAT:g_matrix
        xor     esi, esi
.L12:
        vbroadcastsd    ymm2, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        vbroadcastsd    ymm1, QWORD PTR g_vec[8+rsi*8]
.L11:
        vmovapd ymm0, YMMWORD PTR [rdx+rax]
        vfmadd213pd     ymm0, ymm2, YMMWORD PTR g_out[rax]
        vmovapd YMMWORD PTR g_out[rax], ymm0
        vfmadd231pd     ymm0, ymm1, YMMWORD PTR [rcx+rax]
        add     rax, 32
        vmovapd YMMWORD PTR g_out[rax-32], ymm0
        cmp     rax, 8192
        jne     .L11
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L12
        vzeroupper
        leave
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache()
        vcvttsd2si      eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

`row_cache_unroll4 @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm2, QWORD PTR .LC0[rip]
        push    rbx
        vxorps  xmm1, xmm1, xmm1
        xor     ebx, ebx
        movabs  rcx, 5895351198814392785
.L2:
        mov     rax, rbx
        mul     rcx
        mov     rax, rbx
        sub     rax, rdx
        shr     rax
        add     rdx, rax
        shr     rdx, 6
        imul    rax, rdx, 97
        mov     rdx, rbx
        sub     rdx, rax
        lea     rax, [rdx+1]
        vcvtsi2sd       xmm0, xmm1, rax
        vmulsd  xmm0, xmm0, xmm2
        vmovsd  QWORD PTR g_vec[0+rbx*8], xmm0
        inc     rbx
        cmp     rbx, 1024
        jne     .L2
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     edx, 8192
        call    memset
        xor     esi, esi
        xor     r8d, r8d
        vxorps  xmm1, xmm1, xmm1
        movabs  rdi, -7999030616033345391
.L4:
        mov     rcx, r8
.L3:
        mov     rax, rcx
        mul     rdi
        mov     rax, rcx
        shr     rdx, 6
        imul    rdx, rdx, 113
        sub     rax, rdx
        vcvtsi2sd       xmm0, xmm1, rax
        vmovlpd QWORD PTR g_matrix[rsi+rcx*8], xmm0
        inc     rcx
        cmp     rcx, rbx
        jne     .L3
        inc     r8
        add     rsi, 8184
        lea     rbx, [rcx+1]
        cmp     r8, 1024
        jne     .L4
        pop     rbx
        ret
row_cache_unroll4():
        push    rbp
        mov     edx, 8192
        xor     esi, esi
        mov     edi, OFFSET FLAT:g_out
        mov     rbp, rsp
        and     rsp, -32
        call    memset
        mov     edx, OFFSET FLAT:g_matrix
        xor     esi, esi
.L12:
        vbroadcastsd    ymm2, QWORD PTR g_vec[0+rsi*8]
        lea     rcx, [rdx+8192]
        xor     eax, eax
        vbroadcastsd    ymm1, QWORD PTR g_vec[8+rsi*8]
.L11:
        vmovapd ymm0, YMMWORD PTR [rdx+rax]
        vfmadd213pd     ymm0, ymm2, YMMWORD PTR g_out[rax]
        vmovapd YMMWORD PTR g_out[rax], ymm0
        vfmadd231pd     ymm0, ymm1, YMMWORD PTR [rcx+rax]
        add     rax, 32
        vmovapd YMMWORD PTR g_out[rax-32], ymm0
        cmp     rax, 8192
        jne     .L11
        add     rsi, 2
        add     rdx, 16384
        cmp     rsi, 1024
        jne     .L12
        vzeroupper
        leave
        ret
main:
        sub     rsp, 8
        call    init_data()
        call    row_cache_unroll4()
        vcvttsd2si      eax, QWORD PTR g_out[rip]
        add     rsp, 8
        ret
.LC0:
        .long   0
        .long   1070596096
```

#### 重点观察

- `row_cache_unroll4` 是否减少循环跳转指令
- 是否减少索引更新与边界判断
- 编译器是否进一步向量化

#### 记录模板

- 编译选项：
- 核心汇编特征：
- 与对照函数相比的差异：
- 对性能结果的解释：

#### 可直接写入报告的结论模板

- `row_cache_unroll4` 通过手工展开降低了循环控制开销。
- 若 `-O3` 下二者汇编接近，说明编译器已经对普通版本做了较强优化，手工展开收益可能被部分吸收。

---

## 二、求和组

### 1. `sum_naive` vs `sum_dual`

#### 样例文件

- `sum/sum_naive.cpp`
- `sum/sum_dual.cpp`

#### 建议截图

- `-O0` 下两者核心循环
- `-O3` 下两者核心循环

#### 汇编粘贴区

`sum_naive @ -O0`
```asm
init_data():
        push    rbp
        mov     rbp, rsp
        mov     QWORD PTR [rbp-8], 0
        jmp     .L2
.L5:
        mov     rcx, QWORD PTR [rbp-8]
        movabs  rdx, 367465021388636487
        mov     rax, rcx
        mul     rdx
        mov     rax, rcx
        sub     rax, rdx
        shr     rax
        add     rax, rdx
        shr     rax, 7
        imul    rdx, rax, 251
        mov     rax, rcx
        sub     rax, rdx
        add     rax, 1
        test    rax, rax
        js      .L3
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rax
        jmp     .L4
.L3:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
.L4:
        movsd   xmm1, QWORD PTR .LC0[rip]
        divsd   xmm1, xmm0
        mov     rax, QWORD PTR [rbp-8]
        movsd   QWORD PTR g_data[0+rax*8], xmm1
        add     QWORD PTR [rbp-8], 1
.L2:
        cmp     QWORD PTR [rbp-8], 262143
        jbe     .L5
        nop
        nop
        pop     rbp
        ret
sum_naive():
        push    rbp
        mov     rbp, rsp
        pxor    xmm0, xmm0
        movsd   QWORD PTR [rbp-8], xmm0
        mov     QWORD PTR [rbp-16], 0
        jmp     .L7
.L8:
        mov     rax, QWORD PTR [rbp-16]
        movsd   xmm0, QWORD PTR g_data[0+rax*8]
        movsd   xmm1, QWORD PTR [rbp-8]
        addsd   xmm0, xmm1
        movsd   QWORD PTR [rbp-8], xmm0
        add     QWORD PTR [rbp-16], 1
.L7:
        cmp     QWORD PTR [rbp-16], 262143
        jbe     .L8
        movsd   xmm0, QWORD PTR [rbp-8]
        pop     rbp
        ret
main:
        push    rbp
        mov     rbp, rsp
        sub     rsp, 16
        call    init_data()
        call    sum_naive()
        movq    rax, xmm0
        mov     QWORD PTR [rbp-8], rax
        movsd   xmm0, QWORD PTR [rbp-8]
        cvttsd2si       eax, xmm0
        leave
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_dual @ -O0`
```asm
init_data():
        push    rbp
        mov     rbp, rsp
        mov     QWORD PTR [rbp-8], 0
        jmp     .L2
.L5:
        mov     rcx, QWORD PTR [rbp-8]
        movabs  rdx, 367465021388636487
        mov     rax, rcx
        mul     rdx
        mov     rax, rcx
        sub     rax, rdx
        shr     rax
        add     rax, rdx
        shr     rax, 7
        imul    rdx, rax, 251
        mov     rax, rcx
        sub     rax, rdx
        add     rax, 1
        test    rax, rax
        js      .L3
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rax
        jmp     .L4
.L3:
        mov     rdx, rax
        shr     rdx
        and     eax, 1
        or      rdx, rax
        pxor    xmm0, xmm0
        cvtsi2sd        xmm0, rdx
        addsd   xmm0, xmm0
.L4:
        movsd   xmm1, QWORD PTR .LC0[rip]
        divsd   xmm1, xmm0
        mov     rax, QWORD PTR [rbp-8]
        movsd   QWORD PTR g_data[0+rax*8], xmm1
        add     QWORD PTR [rbp-8], 1
.L2:
        cmp     QWORD PTR [rbp-8], 262143
        jbe     .L5
        nop
        nop
        pop     rbp
        ret
sum_dual():
        push    rbp
        mov     rbp, rsp
        pxor    xmm0, xmm0
        movsd   QWORD PTR [rbp-8], xmm0
        pxor    xmm0, xmm0
        movsd   QWORD PTR [rbp-16], xmm0
        mov     QWORD PTR [rbp-24], 0
        jmp     .L7
.L8:
        mov     rax, QWORD PTR [rbp-24]
        movsd   xmm0, QWORD PTR g_data[0+rax*8]
        movsd   xmm1, QWORD PTR [rbp-8]
        addsd   xmm0, xmm1
        movsd   QWORD PTR [rbp-8], xmm0
        mov     rax, QWORD PTR [rbp-24]
        add     rax, 1
        movsd   xmm0, QWORD PTR g_data[0+rax*8]
        movsd   xmm1, QWORD PTR [rbp-16]
        addsd   xmm0, xmm1
        movsd   QWORD PTR [rbp-16], xmm0
        add     QWORD PTR [rbp-24], 2
.L7:
        mov     rax, QWORD PTR [rbp-24]
        add     rax, 1
        cmp     rax, 262143
        jbe     .L8
        jmp     .L9
.L10:
        mov     rax, QWORD PTR [rbp-24]
        movsd   xmm0, QWORD PTR g_data[0+rax*8]
        movsd   xmm1, QWORD PTR [rbp-8]
        addsd   xmm0, xmm1
        movsd   QWORD PTR [rbp-8], xmm0
        add     QWORD PTR [rbp-24], 1
.L9:
        cmp     QWORD PTR [rbp-24], 262143
        jbe     .L10
        movsd   xmm0, QWORD PTR [rbp-8]
        addsd   xmm0, QWORD PTR [rbp-16]
        pop     rbp
        ret
main:
        push    rbp
        mov     rbp, rsp
        sub     rsp, 16
        call    init_data()
        call    sum_dual()
        movq    rax, xmm0
        mov     QWORD PTR [rbp-8], rax
        movsd   xmm0, QWORD PTR [rbp-8]
        cvttsd2si       eax, xmm0
        leave
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_naive @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_naive():
        mov     eax, OFFSET FLAT:g_data
        pxor    xmm0, xmm0
.L6:
        addsd   xmm0, QWORD PTR [rax]
        add     rax, 16
        addsd   xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        ret
main:
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L9
        mov     eax, OFFSET FLAT:g_data
        pxor    xmm0, xmm0
.L10:
        addsd   xmm0, QWORD PTR [rax]
        add     rax, 16
        addsd   xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        movsd   QWORD PTR [rsp-8], xmm0
        movsd   xmm0, QWORD PTR [rsp-8]
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_dual @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_dual():
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        pxor    xmm1, xmm1
.L6:
        addpd   xmm1, XMMWORD PTR [rax]
        add     rax, 32
        addpd   xmm1, XMMWORD PTR [rax-16]
        cmp     rdx, rax
        jne     .L6
        movapd  xmm0, xmm1
        unpckhpd        xmm1, xmm1
        addsd   xmm0, xmm1
        ret
main:
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L10:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L10
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        pxor    xmm0, xmm0
.L11:
        addpd   xmm0, XMMWORD PTR [rax]
        add     rax, 32
        addpd   xmm0, XMMWORD PTR [rax-16]
        cmp     rdx, rax
        jne     .L11
        movapd  xmm3, xmm0
        unpckhpd        xmm3, xmm3
        movapd  xmm1, xmm3
        addsd   xmm1, xmm0
        movsd   QWORD PTR [rsp-16], xmm1
        movsd   xmm0, QWORD PTR [rsp-16]
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_naive @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_naive():
        mov     eax, OFFSET FLAT:g_data
        vxorpd  xmm0, xmm0, xmm0
.L6:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        add     rax, 32
        vaddsd  xmm0, xmm0, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        ret
main:
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L9
        mov     eax, OFFSET FLAT:g_data
        vxorpd  xmm0, xmm0, xmm0
.L10:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        add     rax, 32
        vaddsd  xmm0, xmm0, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        vmovsd  QWORD PTR [rsp-8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp-8]
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_dual @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_dual():
        vxorpd  xmm1, xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        vmovapd xmm0, xmm1
.L6:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        vaddsd  xmm1, xmm1, QWORD PTR [rax+8]
        add     rax, 64
        vaddsd  xmm0, xmm0, QWORD PTR [rax-48]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-40]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-32]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        vaddsd  xmm0, xmm0, xmm1
        ret
main:
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L9
        vxorpd  xmm1, xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        vmovapd xmm0, xmm1
.L10:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        vaddsd  xmm1, xmm1, QWORD PTR [rax+8]
        add     rax, 64
        vaddsd  xmm0, xmm0, QWORD PTR [rax-48]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-40]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-32]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        vaddsd  xmm0, xmm0, xmm1
        vmovsd  QWORD PTR [rsp-8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp-8]
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

#### 重点观察

- `sum_naive` 是否只有单一累加寄存器
- `sum_dual` 是否出现两条独立累加链
- 指令调度是否更适合超标量执行

#### 记录模板

- 编译选项：
- 核心汇编特征：
- 与对照函数相比的差异：
- 对性能结果的解释：

#### 可直接写入报告的结论模板

- `sum_naive` 的单累加器结构形成长依赖链。
- `sum_dual` 将依赖链拆成两条，编译后更容易并行调度。

---

### 2. `sum_dual` vs `sum_unroll4`

#### 样例文件

- `sum/sum_dual.cpp`
- `sum/sum_unroll4.cpp`

#### 建议截图

- `-O3` 下两者核心循环
- `-O3 -march=native` 下两者核心循环

#### 汇编粘贴区

`sum_dual @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_dual():
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        pxor    xmm1, xmm1
.L6:
        addpd   xmm1, XMMWORD PTR [rax]
        add     rax, 32
        addpd   xmm1, XMMWORD PTR [rax-16]
        cmp     rdx, rax
        jne     .L6
        movapd  xmm0, xmm1
        unpckhpd        xmm1, xmm1
        addsd   xmm0, xmm1
        ret
main:
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L10:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L10
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        pxor    xmm0, xmm0
.L11:
        addpd   xmm0, XMMWORD PTR [rax]
        add     rax, 32
        addpd   xmm0, XMMWORD PTR [rax-16]
        cmp     rdx, rax
        jne     .L11
        movapd  xmm3, xmm0
        unpckhpd        xmm3, xmm3
        movapd  xmm1, xmm3
        addsd   xmm1, xmm0
        movsd   QWORD PTR [rsp-16], xmm1
        movsd   xmm0, QWORD PTR [rsp-16]
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_unroll4 @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        pxor    xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        movapd  xmm2, xmm1
.L6:
        addpd   xmm2, XMMWORD PTR [rax]
        addpd   xmm1, XMMWORD PTR [rax+16]
        add     rax, 32
        cmp     rdx, rax
        jne     .L6
        movapd  xmm3, xmm2
        unpckhpd        xmm3, xmm3
        movapd  xmm0, xmm3
        addsd   xmm0, xmm2
        movapd  xmm2, xmm1
        unpckhpd        xmm1, xmm1
        addsd   xmm1, xmm2
        addsd   xmm0, xmm1
        ret
main:
        movabs  rsi, 2351776136887273513
        sub     rsp, 24
        xor     ecx, ecx
        movsd   xmm2, QWORD PTR .LC0[rip]
.L9:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L9
        call    sum_unroll4()
        movsd   QWORD PTR [rsp+8], xmm0
        movsd   xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_dual @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_dual():
        vxorpd  xmm1, xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        vmovapd xmm0, xmm1
.L6:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        vaddsd  xmm1, xmm1, QWORD PTR [rax+8]
        add     rax, 64
        vaddsd  xmm0, xmm0, QWORD PTR [rax-48]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-40]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-32]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        vaddsd  xmm0, xmm0, xmm1
        ret
main:
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L9
        vxorpd  xmm1, xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        vmovapd xmm0, xmm1
.L10:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        vaddsd  xmm1, xmm1, QWORD PTR [rax+8]
        add     rax, 64
        vaddsd  xmm0, xmm0, QWORD PTR [rax-48]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-40]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-32]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm1, xmm1, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        vaddsd  xmm0, xmm0, xmm1
        vmovsd  QWORD PTR [rsp-8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp-8]
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_unroll4 @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        vxorpd  xmm0, xmm0, xmm0
.L6:
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax]
        add     rax, 64
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax-32]
        cmp     rdx, rax
        jne     .L6
        vunpckhpd       xmm1, xmm0, xmm0
        vaddsd  xmm1, xmm1, xmm0
        vextractf128    xmm0, ymm0, 0x1
        vunpckhpd       xmm2, xmm0, xmm0
        vaddsd  xmm0, xmm2, xmm0
        vaddsd  xmm0, xmm1, xmm0
        vzeroupper
        ret
main:
        sub     rsp, 24
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        movabs  rsi, 2351776136887273513
.L10:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L10
        call    sum_unroll4()
        vmovsd  QWORD PTR [rsp+8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

#### 重点观察

- 四个累加器是否比两个累加器暴露出更多独立计算
- 是否出现更明显的 SIMD 指令
- 是否减少循环控制开销

#### 记录模板

- 编译选项：
- 核心汇编特征：
- 与对照函数相比的差异：
- 对性能结果的解释：

#### 可直接写入报告的结论模板

- `sum_unroll4` 通过更多独立累加寄存器进一步缩短相关路径。
- 若出现 `xmm/ymm` 向量寄存器或向量加法指令，说明编译器自动向量化参与了加速。

---

### 3. `sum_naive` vs `sum_unroll4`

#### 样例文件

- `sum/sum_naive.cpp`
- `sum/sum_unroll4.cpp`

#### 用途

这一组对比最适合直接放在实验报告里，因为它最能体现“基准算法”与“优化算法”之间的差异。

#### 汇编粘贴区

`sum_naive @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_naive():
        mov     eax, OFFSET FLAT:g_data
        pxor    xmm0, xmm0
.L6:
        addsd   xmm0, QWORD PTR [rax]
        add     rax, 16
        addsd   xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        ret
main:
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L9
        mov     eax, OFFSET FLAT:g_data
        pxor    xmm0, xmm0
.L10:
        addsd   xmm0, QWORD PTR [rax]
        add     rax, 16
        addsd   xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        movsd   QWORD PTR [rsp-8], xmm0
        movsd   xmm0, QWORD PTR [rsp-8]
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_unroll4 @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        pxor    xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        movapd  xmm2, xmm1
.L6:
        addpd   xmm2, XMMWORD PTR [rax]
        addpd   xmm1, XMMWORD PTR [rax+16]
        add     rax, 32
        cmp     rdx, rax
        jne     .L6
        movapd  xmm3, xmm2
        unpckhpd        xmm3, xmm3
        movapd  xmm0, xmm3
        addsd   xmm0, xmm2
        movapd  xmm2, xmm1
        unpckhpd        xmm1, xmm1
        addsd   xmm1, xmm2
        addsd   xmm0, xmm1
        ret
main:
        movabs  rsi, 2351776136887273513
        sub     rsp, 24
        xor     ecx, ecx
        movsd   xmm2, QWORD PTR .LC0[rip]
.L9:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L9
        call    sum_unroll4()
        movsd   QWORD PTR [rsp+8], xmm0
        movsd   xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_naive @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_naive():
        mov     eax, OFFSET FLAT:g_data
        vxorpd  xmm0, xmm0, xmm0
.L6:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        add     rax, 32
        vaddsd  xmm0, xmm0, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L6
        ret
main:
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L9:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L9
        mov     eax, OFFSET FLAT:g_data
        vxorpd  xmm0, xmm0, xmm0
.L10:
        vaddsd  xmm0, xmm0, QWORD PTR [rax]
        add     rax, 32
        vaddsd  xmm0, xmm0, QWORD PTR [rax-24]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-16]
        vaddsd  xmm0, xmm0, QWORD PTR [rax-8]
        cmp     rax, OFFSET FLAT:g_data+2097152
        jne     .L10
        vmovsd  QWORD PTR [rsp-8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp-8]
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_unroll4 @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        vxorpd  xmm0, xmm0, xmm0
.L6:
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax]
        add     rax, 64
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax-32]
        cmp     rdx, rax
        jne     .L6
        vunpckhpd       xmm1, xmm0, xmm0
        vaddsd  xmm1, xmm1, xmm0
        vextractf128    xmm0, ymm0, 0x1
        vunpckhpd       xmm2, xmm0, xmm0
        vaddsd  xmm0, xmm2, xmm0
        vaddsd  xmm0, xmm1, xmm0
        vzeroupper
        ret
main:
        sub     rsp, 24
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        movabs  rsi, 2351776136887273513
.L10:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L10
        call    sum_unroll4()
        vmovsd  QWORD PTR [rsp+8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

#### 记录模板

- 编译选项：
- 核心汇编特征：
- 与对照函数相比的差异：
- 对性能结果的解释：

---

### 4. `sum_unroll4` vs `sum_pairwise`（可选）

#### 样例文件

- `sum/sum_unroll4.cpp`
- `sum/sum_pairwise.cpp`

#### 重点观察

- `sum_pairwise` 是否出现更多读写内存的指令
- 是否存在额外的循环层次与写回操作

#### 汇编粘贴区

`sum_unroll4 @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        pxor    xmm1, xmm1
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        movapd  xmm2, xmm1
.L6:
        addpd   xmm2, XMMWORD PTR [rax]
        addpd   xmm1, XMMWORD PTR [rax+16]
        add     rax, 32
        cmp     rdx, rax
        jne     .L6
        movapd  xmm3, xmm2
        unpckhpd        xmm3, xmm3
        movapd  xmm0, xmm3
        addsd   xmm0, xmm2
        movapd  xmm2, xmm1
        unpckhpd        xmm1, xmm1
        addsd   xmm1, xmm2
        addsd   xmm0, xmm1
        ret
main:
        movabs  rsi, 2351776136887273513
        sub     rsp, 24
        xor     ecx, ecx
        movsd   xmm2, QWORD PTR .LC0[rip]
.L9:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_data[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L9
        call    sum_unroll4()
        movsd   QWORD PTR [rsp+8], xmm0
        movsd   xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_pairwise @ -O3`
```asm
init_data():
        movsd   xmm2, QWORD PTR .LC0[rip]
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_work[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L2
        ret
sum_pairwise():
        mov     ecx, 262144
.L9:
        mov     rsi, rcx
        lea     rdx, [rcx-2]
        xor     eax, eax
        and     rsi, -2
.L7:
        movsd   xmm0, QWORD PTR g_work[0+rax*8]
        addsd   xmm0, QWORD PTR g_work[8+rax*8]
        movsd   QWORD PTR g_work[0+rax*4], xmm0
        add     rax, 2
        cmp     rax, rsi
        jne     .L7
        and     rdx, -2
        mov     rax, rcx
        add     rdx, 2
        shr     rax
        cmp     rdx, rcx
        jb      .L12
        cmp     rax, 1
        je      .L13
        mov     rcx, rax
        jmp     .L9
.L13:
        movsd   xmm0, QWORD PTR g_work[rip]
        ret
.L12:
        movsd   xmm0, QWORD PTR g_work[0+rdx*8]
        lea     rcx, [rax+1]
        movsd   QWORD PTR g_work[0+rax*8], xmm0
        jmp     .L9
main:
        movabs  rsi, 2351776136887273513
        sub     rsp, 16
        xor     ecx, ecx
        movsd   xmm2, QWORD PTR .LC0[rip]
.L15:
        mov     rax, rcx
        pxor    xmm1, xmm1
        movapd  xmm0, xmm2
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        add     rax, 1
        cvtsi2sd        xmm1, rax
        divsd   xmm0, xmm1
        movsd   QWORD PTR g_work[0+rcx*8], xmm0
        add     rcx, 1
        cmp     rcx, 262144
        jne     .L15
        call    sum_pairwise()
        movsd   QWORD PTR [rsp+8], xmm0
        movsd   xmm0, QWORD PTR [rsp+8]
        add     rsp, 16
        cvttsd2si       eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_unroll4 @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_unroll4():
        mov     eax, OFFSET FLAT:g_data
        mov     edx, OFFSET FLAT:g_data+2097152
        vxorpd  xmm0, xmm0, xmm0
.L6:
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax]
        add     rax, 64
        vaddpd  ymm0, ymm0, YMMWORD PTR [rax-32]
        cmp     rdx, rax
        jne     .L6
        vunpckhpd       xmm1, xmm0, xmm0
        vaddsd  xmm1, xmm1, xmm0
        vextractf128    xmm0, ymm0, 0x1
        vunpckhpd       xmm2, xmm0, xmm0
        vaddsd  xmm0, xmm2, xmm0
        vaddsd  xmm0, xmm1, xmm0
        vzeroupper
        ret
main:
        sub     rsp, 24
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        movabs  rsi, 2351776136887273513
.L10:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_data[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L10
        call    sum_unroll4()
        vmovsd  QWORD PTR [rsp+8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp+8]
        add     rsp, 24
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

`sum_pairwise @ -O3 -march=native`
```asm
init_data():
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        movabs  rsi, 2351776136887273513
.L2:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_work[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L2
        ret
sum_pairwise():
        mov     ecx, 262144
.L9:
        mov     rsi, rcx
        lea     rdx, [rcx-2]
        xor     eax, eax
        and     rsi, -2
.L7:
        vmovsd  xmm0, QWORD PTR g_work[0+rax*8]
        vaddsd  xmm0, xmm0, QWORD PTR g_work[8+rax*8]
        vmovsd  QWORD PTR g_work[0+rax*4], xmm0
        add     rax, 2
        cmp     rax, rsi
        jne     .L7
        and     rdx, -2
        mov     rax, rcx
        add     rdx, 2
        shr     rax
        cmp     rdx, rcx
        jb      .L12
        cmp     rax, 1
        je      .L13
        mov     rcx, rax
        jmp     .L9
.L13:
        vmovsd  xmm0, QWORD PTR g_work[rip]
        ret
.L12:
        vmovsd  xmm0, QWORD PTR g_work[0+rdx*8]
        lea     rcx, [rax+1]
        vmovsd  QWORD PTR g_work[0+rax*8], xmm0
        jmp     .L9
main:
        sub     rsp, 16
        vxorps  xmm2, xmm2, xmm2
        xor     ecx, ecx
        vmovsd  xmm1, QWORD PTR .LC0[rip]
        movabs  rsi, 2351776136887273513
.L15:
        mov     rax, rcx
        imul    rsi
        mov     rax, rcx
        sar     rax, 63
        sar     rdx, 5
        sub     rdx, rax
        mov     rax, rcx
        imul    rdx, rdx, 251
        sub     rax, rdx
        inc     rax
        vcvtsi2sd       xmm0, xmm2, rax
        vdivsd  xmm0, xmm1, xmm0
        vmovsd  QWORD PTR g_work[0+rcx*8], xmm0
        inc     rcx
        cmp     rcx, 262144
        jne     .L15
        call    sum_pairwise()
        vmovsd  QWORD PTR [rsp+8], xmm0
        vmovsd  xmm0, QWORD PTR [rsp+8]
        add     rsp, 16
        vcvttsd2si      eax, xmm0
        ret
.LC0:
        .long   0
        .long   1072693248
```

#### 可直接写入报告的结论模板

- `sum_pairwise` 虽然在算法结构上具有规约特征，但实现中需要频繁写回中间结果，因此访存开销明显更高。

---

## 三、截图命名建议

建议统一命名，方便后续插入报告：

- `godbolt_matrix_col_naive_o3.png`
- `godbolt_matrix_row_cache_o3.png`
- `godbolt_matrix_row_cache_u4_o3.png`
- `godbolt_sum_naive_o3.png`
- `godbolt_sum_dual_o3.png`
- `godbolt_sum_unroll4_o3.png`

---

## 四、最终整理到报告时的写法

推荐每组只保留：

- 1 张或 2 张核心汇编截图
- 2 到 3 句解释

推荐结构：

1. 说明编译选项
2. 说明观察到的关键汇编现象
3. 将现象与性能测试结果对应起来

示例句式：

- 在 `-O3` 下，`sum_unroll4` 的核心循环包含多条独立累加路径，而 `sum_naive` 仍表现为单一依赖链，这与前者在性能测试中明显更快的现象一致。
- 在 `-O3 -march=native` 下，`row_cache` 对应的核心循环更接近顺序流式访存，说明其性能优势不仅来自算法层面的 cache 友好性，也得到了编译器优化的进一步放大。
