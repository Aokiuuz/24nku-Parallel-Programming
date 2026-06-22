# Godbolt Minimal Cases

这个目录用于 `godbolt.org` 上的汇编分析。

目录结构：

- `matrix/`
  - `col_naive.cpp`
  - `row_cache.cpp`
  - `row_cache_unroll4.cpp`
- `sum/`
  - `sum_naive.cpp`
  - `sum_dual.cpp`
  - `sum_unroll4.cpp`
  - `sum_pairwise.cpp`

## 使用建议

1. 打开 `https://godbolt.org/`
2. 左侧代码窗口粘贴某个 `.cpp` 文件内容
3. 右侧编译器选择：
   - `x86-64 gcc`
   - 或 `x86-64 clang`
4. 依次测试以下编译选项：
   - `-O0 -std=c++17`
   - `-O2 -std=c++17`
   - `-O3 -std=c++17`
   - `-O3 -march=native -std=c++17`
5. 在 Godbolt 右侧开启这些常用选项：
   - `Demangle identifiers`
   - `Filter library code`
   - `Intel syntax`
6. 如果要做函数对比，建议在 Godbolt 里新开多个编译器窗口：
   - 窗口 1：粘贴基准函数
   - 窗口 2：粘贴优化函数
   - 两个窗口都使用同一编译器与同一编译选项

## 推荐对比顺序

### 矩阵组

1. `matrix/col_naive.cpp` vs `matrix/row_cache.cpp`
2. `matrix/row_cache.cpp` vs `matrix/row_cache_unroll4.cpp`
3. 重复以上对比于：
   - `-O0`
   - `-O3`
   - `-O3 -march=native`

重点观察：

- 内层循环是否更紧凑
- 地址计算是否更简单
- 是否出现向量寄存器或自动展开
- `row_cache_unroll4` 是否减少了循环控制指令

### 求和组

1. `sum/sum_naive.cpp` vs `sum/sum_dual.cpp`
2. `sum/sum_dual.cpp` vs `sum/sum_unroll4.cpp`
3. `sum/sum_naive.cpp` vs `sum/sum_unroll4.cpp`
4. 可选：`sum/sum_unroll4.cpp` vs `sum/sum_pairwise.cpp`

重点观察：

- 是否仍是单条累加依赖链
- 是否拆成多条独立累加链
- 是否出现 SIMD 指令
- 是否减少了分支和循环控制

## 报告里建议保留的结果

- 每组实验保留 1 到 2 张核心汇编截图
- 每个截图配 2 到 3 句解释
- 不要贴整页汇编，只截核心循环

可直接写入报告的结论模板：

- `col_naive` 的核心循环包含跨行访存，对地址计算和 cache 行为都不友好。
- `row_cache` 的内层访问更连续，编译器更容易生成紧凑的加载与乘加序列。
- `sum_naive` 只有一个累加器，形成长依赖链。
- `sum_dual` 和 `sum_unroll4` 使用多个累加器，降低数据相关，更利于指令级并行。
