# VTune 分析结果目录

这个目录用于整理 Intel VTune 的分析截图、记录表和文字总结。

## 建议结构

- `matrix/`
  - `hotspots/`
  - `memory_access/`
- `sum/`
  - `hotspots/`
  - `microarchitecture/`

## 建议保存内容

每次分析至少保存：

1. Summary 截图
2. 函数级对比截图
3. 源码热点截图
4. 一份文字记录：
   - 程序名
   - 参数
   - 分析类型
   - 关键指标
   - 一句话结论

## 推荐命名

### 矩阵题

- `matrix_hotspots_1024_summary.png`
- `matrix_hotspots_1024_bottomup.png`
- `matrix_hotspots_1024_source.png`
- `matrix_memory_1024_summary.png`
- `matrix_memory_1024_functions.png`
- `matrix_memory_1024_source.png`

### 求和题

- `sum_hotspots_262144_summary.png`
- `sum_hotspots_262144_bottomup.png`
- `sum_micro_262144_summary.png`
- `sum_micro_262144_topdown.png`
- `sum_micro_262144_functions.png`
- `sum_micro_4194304_summary.png`

## 推荐实验顺序

1. `matrix_dot_vtune.exe 1024` 跑 `Hotspots`
2. `matrix_dot_vtune.exe 1024` 跑 `Memory Access`
3. `sum_bench_vtune.exe 262144` 跑 `Hotspots`
4. `sum_bench_vtune.exe 262144` 跑 `Microarchitecture Exploration`
5. `sum_bench_vtune.exe 4194304` 跑 `Hotspots`
6. `sum_bench_vtune.exe 4194304` 跑 `Microarchitecture Exploration`
