# Lab01 Results Summary

本文件整理了当前实验框架在 `-O0`、`-O2`、`-O3` 三种编译优化等级下的运行结果，并说明每组数据的含义。

## 字段说明

- `algorithm`：算法名称
- `size`：问题规模
- `repeat`：重复执行次数
- `seconds`：重复执行 `repeat` 次的总耗时，单位秒
- `speedup`：相对基础算法的加速比

加速比计算方式：

```text
speedup = baseline_time / current_time
```

- 对矩阵题，基准算法是 `col_naive`
- 对求和题，基准算法是 `sum_naive`

解释：

- `speedup > 1`：当前算法更快
- `speedup = 1`：和基准算法一样
- `speedup < 1`：当前算法更慢

---

## 一、矩阵列内积

算法对应关系：

- `col_naive`：按列访问矩阵的平凡算法
- `row_cache`：按行访问矩阵的 cache 优化算法
- `row_cache_u4`：按行访问 + 4 路循环展开

### 1. `-O0`

```text
=== matrix column dot product ===
algorithm           size        repeat      seconds         speedup
col_naive           128         400         0.035911        1.000
row_cache           128         400         0.032405        1.108
row_cache_u4        128         400         0.032201        1.115
col_naive           256         120         0.045614        1.000
row_cache           256         120         0.038836        1.175
row_cache_u4        256         120         0.038891        1.173
col_naive           512         30          0.066748        1.000
row_cache           512         30          0.038642        1.727
row_cache_u4        512         30          0.038735        1.723
col_naive           1024        8           0.232900        1.000
row_cache           1024        8           0.036803        6.328
row_cache_u4        1024        8           0.044080        5.284
```

### 2. `-O2`

```text
=== matrix column dot product ===
algorithm           size        repeat      seconds         speedup
col_naive           128         400         0.005892        1.000
row_cache           128         400         0.002102        2.803
row_cache_u4        128         400         0.001640        3.592
col_naive           256         120         0.005733        1.000
row_cache           256         120         0.002111        2.715
row_cache_u4        256         120         0.001892        3.030
col_naive           512         30          0.006746        1.000
row_cache           512         30          0.002036        3.313
row_cache_u4        512         30          0.001957        3.447
col_naive           1024        8           0.048577        1.000
row_cache           1024        8           0.004488        10.824
row_cache_u4        1024        8           0.003531        13.758
```

### 3. `-O3`

```text
=== matrix column dot product ===
algorithm           size        repeat      seconds         speedup
col_naive           128         400         0.005127        1.000
row_cache           128         400         0.001258        4.077
row_cache_u4        128         400         0.000972        5.274
col_naive           256         120         0.005754        1.000
row_cache           256         120         0.001380        4.170
row_cache_u4        256         120         0.001369        4.203
col_naive           512         30          0.007091        1.000
row_cache           512         30          0.001192        5.951
row_cache_u4        512         30          0.001243        5.704
col_naive           1024        8           0.043438        1.000
row_cache           1024        8           0.003575        12.151
row_cache_u4        1024        8           0.003100        14.011
```

### 4. 结果解释

1. `row_cache` 基本都明显快于 `col_naive`
   - 说明按行访问更符合 C/C++ 的行主存储方式。
   - 连续访问内存时，cache 更容易命中。

2. 问题规模越大，`row_cache` 的优势越明显
   - 尤其在 `size=1024` 时，加速比可达到 `10x` 以上。
   - 说明数据规模增大后，访存模式对性能的影响更明显。

3. `row_cache_u4` 通常比 `row_cache` 更快或接近
   - 这体现了循环展开的收益：减少循环判断、索引更新等控制开销。
   - 但它不是对所有规模都严格最优，说明展开收益会受到编译器和寄存器分配的影响。

4. `-O0`、`-O2`、`-O3` 差异很明显
   - `-O0` 下整体最慢。
   - `-O2` 和 `-O3` 下，cache 优化和 `unroll` 才能更明显地发挥作用。

---

## 二、n 个数求和

算法对应关系：

- `sum_naive`：单链式累加
- `sum_dual`：两路链式累加
- `sum_unroll4`：四路累加
- `sum_pairwise`：两两相加的树形求和

### 1. `-O0`

```text
=== sum n numbers ===
algorithm           size        repeat      seconds         speedup
sum_naive           1024        20000       0.041079        1.000
sum_dual            1024        20000       0.070381        0.584
sum_unroll4         1024        20000       0.064958        0.632
sum_pairwise        1024        20000       0.190056        0.216
sum_naive           16384       4000        0.128563        1.000
sum_dual            16384       4000        0.223203        0.576
sum_unroll4         16384       4000        0.210417        0.611
sum_pairwise        16384       4000        0.665581        0.193
sum_naive           262144      600         0.338992        1.000
sum_dual            262144      600         0.566687        0.598
sum_unroll4         262144      600         0.474945        0.714
sum_pairwise        262144      600         1.428311        0.237
sum_naive           4194304     80          0.729098        1.000
sum_dual            4194304     80          1.257167        0.580
sum_unroll4         4194304     80          1.137982        0.641
sum_pairwise        4194304     80          3.279034        0.222
```

### 2. `-O2`

```text
=== sum n numbers ===
algorithm           size        repeat      seconds         speedup
sum_naive           1024        20000       0.008649        1.000
sum_dual            1024        20000       0.004537        1.906
sum_unroll4         1024        20000       0.002311        3.742
sum_pairwise        1024        20000       0.006870        1.259
sum_naive           16384       4000        0.039790        1.000
sum_dual            16384       4000        0.016440        2.420
sum_unroll4         16384       4000        0.007876        5.052
sum_pairwise        16384       4000        0.029359        1.355
sum_naive           262144      600         0.076637        1.000
sum_dual            262144      600         0.045045        1.701
sum_unroll4         262144      600         0.020669        3.708
sum_pairwise        262144      600         0.419883        0.183
sum_naive           4194304     80          0.214646        1.000
sum_dual            4194304     80          0.164202        1.307
sum_unroll4         4194304     80          0.163617        1.312
sum_pairwise        4194304     80          1.111949        0.193
```

### 3. `-O3`

```text
=== sum n numbers ===
algorithm           size        repeat      seconds         speedup
sum_naive           1024        20000       0.009025        1.000
sum_dual            1024        20000       0.004388        2.057
sum_unroll4         1024        20000       0.002246        4.018
sum_pairwise        1024        20000       0.007210        1.252
sum_naive           16384       4000        0.031813        1.000
sum_dual            16384       4000        0.015477        2.055
sum_unroll4         16384       4000        0.007777        4.091
sum_pairwise        16384       4000        0.029042        1.095
sum_naive           262144      600         0.095107        1.000
sum_dual            262144      600         0.045808        2.076
sum_unroll4         262144      600         0.021920        4.339
sum_pairwise        262144      600         0.377787        0.252
sum_naive           4194304     80          0.190002        1.000
sum_dual            4194304     80          0.137766        1.379
sum_unroll4         4194304     80          0.140909        1.348
sum_pairwise        4194304     80          0.993874        0.191
```

### 4. 结果解释

1. `-O0` 下，`sum_dual` 和 `sum_unroll4` 反而通常比 `sum_naive` 更慢
   - 说明如果编译器几乎不做优化，额外的变量和展开代码不一定有收益。
   - 手工优化是否有效，往往依赖编译器和目标平台。

2. `-O2` 和 `-O3` 下，`sum_dual` 和 `sum_unroll4` 明显更快
   - 说明多路累加减少了单一累加变量上的依赖链。
   - 对超标量 CPU 来说，这样更容易同时执行多条互不依赖的加法指令。

3. `sum_unroll4` 通常比 `sum_dual` 还要更快
   - 说明四路累加 + 循环展开在多数规模下效果更好。
   - 这正体现了进阶要求中的 `unroll` 技术。

4. `sum_pairwise` 作为补充算法思路，在小规模下偶尔接近或略优，但大规模下明显更慢
   - 原因是它需要大量中间结果写回数组，访存开销更高。
   - 因此它适合体现“更多算法设计思路”，但不一定是当前实现中的最快算法。

5. 大规模下，`sum_dual` 和 `sum_unroll4` 的优势会缩小
   - 可能是因为数据规模过大后，性能瓶颈逐渐从运算依赖转向内存访问。

---

## 三、如何对应实验要求

### 基本要求

- 矩阵题：
  - `col_naive`
  - `row_cache`
- 求和题：
  - `sum_naive`
  - `sum_dual`
- 都完成了正确性验证、计时和性能对比

### 进阶要求 1：循环展开

- 矩阵题：`row_cache_u4`
- 求和题：`sum_unroll4`

### 进阶要求 2：补充更多算法设计思路

- 求和题：`sum_pairwise`

### 进阶要求 3：比较编译器优化力度

- 已对比：
  - `-O0`
  - `-O2`
  - `-O3`

---

## 四、可直接写入报告的结论

1. 矩阵列内积实验表明，按行访问矩阵比按列访问矩阵更快，说明 cache 局部性对性能影响显著。
2. 随着矩阵规模增大，cache 优化算法的优势更加明显，体现了访存模式和 cache 大小之间的关系。
3. `n` 个数求和实验表明，多路链式累加在 `-O2/-O3` 下显著优于单链式累加，说明减少指令依赖、提高指令级并行是有效的。
4. 四路展开通常优于两路累加，说明循环展开能进一步减少循环控制开销并提高性能。
5. 树形求和是一种值得研究的额外算法思路，但当前实现中由于中间结果写回带来的访存开销较大，在大规模数据下性能不占优。
6. 编译器优化等级对性能影响极大，`-O0` 下很多手工优化难以体现优势，而 `-O2/-O3` 下优化效果明显增强。
