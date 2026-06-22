# Lab04 口令猜测 MPI 加速实现说明

## 1. Lab4 要求与实现证据

本实现针对 `kits/2026并行程序设计Lab4_MPI编程.pdf` 的口令猜测选题，并结合
Lab2 的 NEON SIMD MD5、Lab3 的 Pthread/OpenMP 要求以及两张 Lab4 要求截图完成。
代码分为阻塞式基础版和混合流水线进阶版，便于在报告中逐项对比。

| Lab4 要求 | 实现方式 | 代码证据 | 当前状态 |
|---|---|---|---|
| 使用 MPI 进程编程 | 两个版本均使用 `MPI_Init_thread`、Rank、消息通信和 `MPI_Finalize` | 两个版本的 `main.cpp` | 代码满足 |
| 从单个 PT 扩展为多个 PT 并行生成 | Rank 0 连续调用 `PopNextTask()`，同时向多个 Worker 或生成线程分配不同 PT | `guess_mpi_base/main.cpp` 的 `RunMaster()`；`guess_mpi_advanced/main.cpp` 的 `AssignWorkUnits()` | 代码满足 |
| 设计任务分配算法 | 基础版使用完整 PT 动态调度；进阶版使用 `WorkUnit = PT + [begin,end)` 范围切片和最小负载分配 | `PCFG.h`、`guessing.cpp` | 代码满足 |
| Worker 完成指定 PT 的口令生成和 MD5 | 基础版 Worker 接收打包后的 PT，调用 `GenerateRange()` 并分批执行 MD5 | `guess_mpi_base/main.cpp` 的 `RunWorker()` | 代码满足 |
| 实现口令生成与加密流水线 | 进阶版的生成线程、MPI 主线程和加密 Worker 同时工作 | `guess_mpi_advanced/main.cpp` 的 `GeneratorMain()`、`RunPipelineMaster()`、`RunEncryptionWorker()` | 代码满足 |
| 实现图 6.4 的生成进程、线程缓存和加密进程结构 | Rank 0 默认启动 3 个 Pthread，每个线程拥有独立有界缓存；Rank 0 主线程轮询缓存并发送给多个加密进程 | `GeneratorContext`、`PushReadyBatch()`、`PopReadyBatch()` | 代码满足 |
| MPI 与 Pthread、SIMD 结合 | Rank 0 使用 Pthread 生成口令；加密 Worker 使用四路 ARM NEON MD5 | 进阶版 `main.cpp` 与 `mpi_support.cpp::HashGuesses()` | 代码满足 |
| 比较不同 MPI 编程方法 | 基础版使用阻塞式 `MPI_Send/MPI_Recv`；进阶版使用 `MPI_Isend/MPI_Irecv/MPI_Waitany` | 两个版本的 `main.cpp`、`mpi_support.cpp` | 代码满足，性能结果待服务器填写 |
| 负载均衡 | Worker 完成后立即获得下一 PT；进阶版还会切分大型 PT，并按预计口令数分配给当前负载最小的生成线程 | `NextWholePt()`、`SplitTask()`、`AssignWorkUnits()` | 代码满足 |
| 测试不同问题规模、进程数和线程数 | 支持 `--generate`、`--batch-guesses`、`--batch-units`、`--gen-threads` 参数 | `mpi_support.cpp::ParseOptions()` | 实验方案满足，结果待服务器填写 |
| 分析串行与并行性能 | 输出训练时间、生成关键路径时间、哈希关键路径时间、通信时间、总墙钟时间和处理口令数 | 两个版本的 `main.cpp` | 输出满足，结果待服务器填写 |
| 保留和结合 SIMD | 默认调用 backup 已实现并验证的四路 NEON `MD5Hash_simdversion()`；`--serial` 可切换串行 MD5 | `mpi_support.cpp::HashGuesses()` | 代码满足 |
| 撰写不超过 20 页的研究报告 | 本文档给出要求对应、算法、实验设计、结果表和分析方法，可作为报告主体 | 本文件 | 已提供报告材料 |

需要注意：代码能够满足算法与程序结构要求，但“不同规模、不同进程数下的性能分析”
必须在 ARM MPI 服务器实际运行后填写。本文档不会伪造加速比。

## 2. 目录和文件

原始目录 `ARM_code/guess_mpi_backup` 保持不动。新增目录如下：

```text
ARM_code/
├── guess_mpi_backup/       原始 SIMD 版本，不修改
├── guess_mpi_base/         阻塞式 Master-Worker 基础版
└── guess_mpi_advanced/     MPI + Pthread + NEON 流水线进阶版
```

两个新版本中的公共文件：

- `PCFG.h`：增加 `WorkUnit` 和任务化接口声明。
- `guessing.cpp`：增加 `PopNextTask()`、`GuessCount()`、`SplitTask()` 和 `GenerateRange()`。
- `mpi_support.h/.cpp`：参数解析、MPI 打包、批量 MD5 和基础版通信协议。
- `md5.cpp/.h`：沿用 backup 的串行 MD5 和四路 ARM NEON MD5。
- `train.cpp`：沿用 backup 的 PCFG 训练流程。

## 3. 原始程序和任务化改造

### 3.1 原始执行过程

backup 在一个进程中依次执行：

```text
训练 PCFG
  -> 优先队列取出一个 PT
  -> 根据 PT 最后一个 segment 的全部 value 生成口令
  -> 累积口令
  -> 对口令执行串行或四路 NEON MD5
```

PT 表示一个具体的 PCFG preterminal 状态。例如，某个 `L6D2` PT 已经固定 `L6`
的 value，最后一个 `D2` segment 的所有 value 就是可并行生成的口令范围。

### 3.2 WorkUnit

新增的工作单元为：

```cpp
struct WorkUnit {
    PT pt;
    uint64_t begin;
    uint64_t end;
};
```

`[begin,end)` 表示只遍历最后一个 segment 的指定 value 范围。因此：

- 基础版使用 `[0, GuessCount(pt))`，一个任务就是一个完整 PT。
- 进阶版使用多个较小范围切分大型 PT，避免一个大 PT 长时间独占线程。

新增接口职责：

- `PopNextTask()`：从优先队列取出当前 PT、生成并插入后继 PT，但不立即生成口令。
- `GuessCount()`：计算 PT 或 WorkUnit 将生成多少条口令。
- `SplitTask()`：按照 `--batch-guesses` 将大 PT 切成多个 WorkUnit。
- `GenerateRange()`：生成一个 WorkUnit 范围内的口令。

### 3.3 MPI 序列化

`PT` 包含 `std::vector`，不能直接发送对象内存。基础版使用 `MPI_Pack/MPI_Unpack`
只发送重建 PT 所需的数据：

```text
segment 数量
每个 segment 的 type 和 length
pivot
curr_indices
max_indices
preterm_prob 和 prob
WorkUnit 的 begin 和 end
```

Worker 已独立训练相同 PCFG 模型，因此收到这些索引后可以定位相同 segment value，
不需要传输庞大的模型或全部口令字符串。

## 4. 基础版：阻塞式 Master-Worker

### 4.1 结构

```text
Rank 0 Master
  ├── 维护唯一 PCFG 优先队列
  ├── 向 Worker 1 发送 PT1
  ├── 向 Worker 2 发送 PT2
  └── 某个 Worker 完成后立即向它发送下一个 PT

Rank 1..N Worker
  └── 接收完整 PT -> 分批生成口令 -> NEON MD5 -> 返回统计数据
```

基础版直接满足 Lab4 口令猜测专项提出的 Master-Worker 要求：Master 分配
preterminal，Worker 完成指定 preterminal 的口令生成和 MD5。

### 4.2 动态调度

Master 首先向每个 Worker 发送一个不同 PT，然后通过
`MPI_Recv(..., MPI_ANY_SOURCE, ...)` 接收任意完成的 Worker。完成较快的 Worker
会立即获得下一任务，因此比固定静态分配更能适应不同 PT 的规模差异。

基础版有意使用阻塞式 `MPI_Send/MPI_Recv`，作为进阶版非阻塞通信的对照组。

## 5. 进阶版：生成与加密流水线

### 5.1 对应 Lab4 图 6.3 和图 6.4

```text
Rank 0 生成进程
  ├── Generator Thread 0 -> 独立有界缓存 0
  ├── Generator Thread 1 -> 独立有界缓存 1
  ├── Generator Thread 2 -> 独立有界缓存 2
  └── Rank 0 主线程轮询 READY 缓存并执行 MPI 非阻塞发送

Rank 1..N 加密进程
  └── 接收口令批次 -> 四路 ARM NEON MD5 -> 返回完成统计
```

生成线程、MPI 发送和多个加密进程可以重叠执行。当加密进程处理上一批口令时，
生成线程继续准备下一批，从而实现流水线。

### 5.2 MPI 线程级别

进阶版调用：

```cpp
MPI_Init_thread(..., MPI_THREAD_FUNNELED, ...);
```

只有 Rank 0 主线程调用 MPI。Pthread 生成线程仅调用只读的 `GenerateRange()` 并写入
自己的缓存，不调用 `MPI_Pack`、`MPI_Send` 等 MPI 函数。这既满足 MPI 与多线程结合，
也避免请求开销更高且服务器未必完整支持的 `MPI_THREAD_MULTIPLE`。

### 5.3 缓存与同步

每个 `GeneratorContext` 拥有：

- 独立 WorkUnit 队列。
- 独立 READY 口令批次队列。
- 独立互斥锁和条件变量。
- 最多两个 READY 批次的有界缓存。

缓存满时生成线程等待，主线程取走批次后发送条件信号。这是生产者-消费者模型，
同时限制内存使用。

### 5.4 非阻塞通信与缓冲区生命周期

Rank 0 主线程为每个加密 Worker 保存独立 `outbound[worker]` 缓冲区，并执行：

```text
MPI_Irecv：提前接收 Worker 完成结果
MPI_Isend：发送该 Worker 的口令批次
MPI_Testany/MPI_Waitany：发现任意完成的 Worker
MPI_Wait：确认发送完成后才允许复用 outbound[worker]
```

因此非阻塞发送期间缓冲区不会被覆盖。Worker 完成后立即变为空闲状态并获得下一批，
实现动态负载均衡。

### 5.5 PT 切分与批量策略

- 大 PT 按最后一个 segment 的 value 范围切分，每个 WorkUnit 目标不超过
  `--batch-guesses` 条口令。
- 小 WorkUnit 可以由生成线程合并，直到口令数达到 `--batch-guesses` 或 WorkUnit
  数达到 `--batch-units`。
- WorkUnit 根据预计口令数分配给当前累计负载最小的生成线程。

该策略同时降低大型 PT 造成的尾部延迟，并减少过多小消息造成的通信开销。

## 6. NEON SIMD MD5

`mpi_support.cpp::HashGuesses()` 默认每次取四条口令调用：

```cpp
MD5Hash_simdversion(&guesses[i], state);
```

不足四条的尾部使用串行 `MD5Hash()`。命令行加入 `--serial` 后全部使用串行 MD5，
用于对比：

```text
MPI + serial MD5
MPI + NEON SIMD MD5
MPI + Pthread pipeline + NEON SIMD MD5
```

Rank 0 在开始训练前执行 backup 中已有的串行和 SIMD MD5 正确性测试，并将结果广播
给所有 Rank。测试失败时所有进程均调用 `MPI_Finalize()` 后退出。

## 7. ARM 服务器编译和运行

### 7.1 编译

在 ARM 服务器当前节点仅编译，不直接执行：

```bash
cd ~/guess_mpi_base
mpic++ -O2 main.cpp train.cpp guessing.cpp md5.cpp mpi_support.cpp \
  -o main -fopenmp

cd ~/guess_mpi_advanced
mpic++ -O2 main.cpp train.cpp guessing.cpp md5.cpp mpi_support.cpp \
  -o main -pthread -fopenmp
```

### 7.2 MPI 启动

MPI 程序必须由多个 Rank 启动，等价命令示例如下：

```bash
mpiexec -n 4 ./main --generate 10000000
mpiexec -n 4 ./main --generate 10000000 --serial
mpiexec -n 8 ./main --generate 10000000 --gen-threads 3 \
  --batch-guesses 100000 --batch-units 64
```

服务器指南要求必须通过官方 `test.sh/qsub.sh` 提交，且不得修改加密脚本。因此实际提交
时应使用助教提供的 MPI 版启动脚本或请助教确认 Rank 数配置，不能私自修改
`guess_mpi_backup/test.sh`。本地新增目录没有复制或修改官方脚本。

## 8. 必做实验矩阵

以下实验用于满足 Lab4 的“不同问题规模、不同节点数/线程数、串行和并行对比”要求。

### 8.1 正确性

| 版本 | 进程数 | 参数 | MD5 测试 | 是否正常结束 | Processed guesses |
|---|---:|---|---|---|---:|
| base | 1 | `--generate 1000000` | 待填 | 待填 | 待填 |
| base | 4 | `--generate 1000000` | 待填 | 待填 | 待填 |
| advanced | 4 | `--generate 1000000 --gen-threads 3` | 待填 | 待填 | 待填 |

### 8.2 问题规模和进程数

| 版本 | Generate 数量 | MPI 进程数 | 总墙钟时间/s | Guess time/s | Hash time/s | 加速比 |
|---|---:|---:|---:|---:|---:|---:|
| base | 1,000,000 | 1 | 待填 | 待填 | 待填 | 1.00 |
| base | 1,000,000 | 2/4/8 | 待填 | 待填 | 待填 | 待填 |
| base | 5,000,000 | 1/2/4/8 | 待填 | 待填 | 待填 | 待填 |
| base | 10,000,000 | 1/2/4/8 | 待填 | 待填 | 待填 | 待填 |
| advanced | 10,000,000 | 2/4/8/16 | 待填 | 待填 | 待填 | 待填 |

### 8.3 线程数、批次和 SIMD

| 版本 | 进程数 | 生成线程数 | Batch guesses | MD5 | 总墙钟时间/s | 通信时间/s |
|---|---:|---:|---:|---|---:|---:|
| advanced | 8 | 1/2/3/4 | 100,000 | NEON | 待填 | 待填 |
| advanced | 8 | 3 | 25,000/100,000/250,000 | NEON | 待填 | 待填 |
| advanced | 8 | 3 | 100,000 | serial/NEON | 待填 | 待填 |

### 8.4 必须比较的算法

报告至少比较：

1. backup 单进程 NEON 基线。
2. `guess_mpi_base` 阻塞式单 PT 动态调度。
3. `guess_mpi_advanced` 非阻塞流水线。
4. `--serial` 与默认 NEON，用于分析 MPI 和 SIMD 组合收益。

## 9. 性能分析方法

使用 MPI 总墙钟时间计算：

```text
加速比 S(p) = T(1) / T(p)
并行效率 E(p) = S(p) / p
通信占比 = MPI communication time / MPI wall time
```

重点分析以下现象：

- 基础版发送紧凑 PT，通信量小，但 Worker 同时承担生成和 MD5，PT 大小不均会产生尾部等待。
- 进阶版切分大 PT 并重叠生成和 MD5，负载更均衡，但需要发送口令字符串，通信量明显增加。
- 批次过小会增加 MPI 消息次数；批次过大则降低流水线灵活性并增加尾部延迟。
- Rank 数增加后，训练时间不会下降；总时间可能受网络通信、Master 发送能力和内存带宽限制。
- NEON 仅加速 MD5 部分。当生成或通信成为瓶颈时，整体加速比不会等于 MD5 的局部加速比。

程序保留以下三行原有输出格式：

```text
Guess time:...seconds
Hash time:...seconds
Train time:...seconds
```

同时增加 MPI 总墙钟时间、通信时间、进程数、生成线程数和实际处理口令数，便于报告分析。
基础版输出的是阻塞式 `MPI communication/wait time`，其中包含 Master 等待 Worker
结果的时间；进阶版输出的是主线程执行打包、非阻塞通信和完成处理的累计时间。二者应
结合总墙钟时间和 Worker 关键路径一起解释，不能直接当作纯网络传输延迟。

## 10. 静态检查与服务器验收

### 10.1 已完成的静态检查

- `guess_mpi_backup` 未被编辑，新增代码仅位于两个新目录。
- 两个版本均在正常路径、线程级别不足路径和正确性失败路径调用 `MPI_Finalize()`。
- 基础版使用 `MPI_Pack/MPI_Unpack`，不直接发送含 STL 容器的 PT 对象。
- 进阶版只有 Rank 0 主线程调用 MPI，符合 `MPI_THREAD_FUNNELED`。
- 每个非阻塞发送 Worker 拥有独立缓冲区，并在 `MPI_Wait()` 后才复用。
- 每个生成线程拥有独立缓存；共享访问由互斥锁和条件变量保护。
- Rank 0 独占优先队列的修改，生成线程只读取训练完成后的模型。
- 串行和 NEON MD5 路径均被保留。
- 两个新增目录未复制二进制、历史性能结果或官方 `test.sh/qsub.sh`。
- 已使用 `cppcheck` 对两个版本执行纯静态分析；未发现新增 MPI/Pthread 路径中的
  明确正确性错误。工具报告的 MD5 padding、构造函数写法和参数传值提示均来自
  backup 原有代码，本次为保持基线口径未修改。

### 10.2 ARM 服务器必须完成的验收

由于本地不是目标 ARM MPI 服务器，本次未执行编译或运行。提交前必须在服务器确认：

1. 使用服务器 MPI 编译器成功编译两个版本。
2. 使用 1、2、4、8 个 Rank 均能正常结束，无死锁。
3. 串行和 SIMD MD5 正确性测试均通过。
4. `Processed guesses` 在相同参数下保持可解释的一致性。
5. 所有 Worker 均收到停止消息，任务结束后 `qstat` 不残留作业。
6. 填写第 8 节实验表，并在报告中计算加速比、并行效率和通信占比。

## 11. 保留的 backup 语义和已知限制

- 保留 backup 中 `segment::order()` 重复累计频数的行为，避免改变原有 PCFG 排序与对比口径。
- 保留“完成整个 PT 后才停止”的语义，因此实际 `Processed guesses` 可能略高于
  `--generate`。
- 所有 Rank 独立训练 PCFG，以便基础版 Worker 根据 PT 索引生成口令；训练阶段不属于
  本次 MPI 加速目标。
- 基础版结果统计使用每个 Worker 累计时间的最大值表示关键路径。
- 进阶版 Rank 0 是集中式生成与通信节点；当加密进程数很多时，Rank 0 可能成为瓶颈，
  这正是实验中需要通过通信占比和扩展性曲线分析的内容。
