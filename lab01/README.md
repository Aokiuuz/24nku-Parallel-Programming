# Lab01 C++ Experiment Framework

这个框架覆盖：

- 基本要求
  - 矩阵列内积：`col_naive`、`row_cache`
  - `n` 个数求和：`sum_naive`、`sum_dual`
- 进阶要求
  - `unroll`：`row_cache_unroll4`、`sum_unroll4`
  - 更多算法设计：`sum_pairwise`
  - 编译器优化力度对比：`Makefile` 提供 `o0/o2/o3`

## 目录

```text
lab01/
  Makefile
  README.md
  src/
    common.hpp
    matrix_dot.cpp
    sum_bench.cpp
```

## 编译

要求本机已安装 `g++` 和 `make`。

```bash
make o0
make o2
make o3
```

如果你在 Windows 的 MinGW 环境中，通常是：

```bash
mingw32-make o0
mingw32-make o2
mingw32-make o3
```

如果你不用 `make`，也可以直接编译：

```bash
g++ -std=c++17 -O2 -Wall -Wextra src/matrix_dot.cpp -o bin/matrix_dot_o2
g++ -std=c++17 -O2 -Wall -Wextra src/sum_bench.cpp -o bin/sum_bench_o2
```

## 执行

默认运行：

```bash
./bin/matrix_dot_o2
./bin/sum_bench_o2
```

自定义规模：

```bash
./bin/matrix_dot_o2 128 256 512 1024 2048
./bin/sum_bench_o2 1024 4096 16384 65536 262144
```

Windows PowerShell 示例：

```powershell
.\bin\matrix_dot_o2.exe 128 256 512 1024 2048
.\bin\sum_bench_o2.exe 1024 4096 16384 65536 262144
```

## 输出解释

- `algorithm`：算法名称
- `size`：问题规模
- `repeat`：重复次数
- `seconds`：总运行时间
- `speedup`：相对基础算法的加速比

## 报告建议

- 矩阵题比较 `col_naive`、`row_cache`、`row_cache_u4`
- 求和题比较 `sum_naive`、`sum_dual`、`sum_unroll4`、`sum_pairwise`
- 分别测试 `-O0`、`-O2`、`-O3`
- 结果整理成表格和图，不要直接贴终端截图
