# guess-omp 相对 guess-serial 的修改说明

## 修改范围

本版本只修改了 `guessing.cpp` 中 PCFG 口令生成阶段，没有改动训练、MD5 哈希、`main.cpp` 的哈希与清理流程。

串行版本的主要瓶颈在 `PriorityQueue::Generate(PT pt)` 里的两个循环：

1. 当 PT 只有一个 segment 时，遍历该 segment 的全部 `ordered_values`，逐个 `push_back` 到 `guesses`。
2. 当 PT 有多个 segment 时，先串行拼出最后一个 segment 之前的前缀，再遍历最后一个 segment 的全部 `ordered_values`，生成 `prefix + value`。

这两个循环中每个 value 生成一个独立口令，循环迭代之间没有依赖，因此适合用 OpenMP 并行。

## 新增辅助函数

在 `guessing.cpp` 文件开头新增匿名命名空间：

```cpp
const int kOpenMpChunk = 256;

void AppendSegmentValuesOpenMP(vector<string> &output,
                               const vector<string> &values,
                               int value_count);

void AppendPrefixedSegmentValuesOpenMP(vector<string> &output,
                                       const string &prefix,
                                       const vector<string> &values,
                                       int value_count);
```

两个函数的作用分别是：

- `AppendSegmentValuesOpenMP`：处理单 segment PT，直接把 `values[i]` 写入结果。
- `AppendPrefixedSegmentValuesOpenMP`：处理多 segment PT，把已确定的前缀 `prefix` 和最后一个 segment 的 `values[i]` 拼接后写入结果。

## 并行实现方式

串行版本在循环中直接执行：

```cpp
guesses.emplace_back(guess);
total_guesses += 1;
```

OpenMP 版本改为先扩展结果数组：

```cpp
const size_t base = output.size();
output.resize(base + value_count);
```

然后用 OpenMP 并行写入不同下标：

```cpp
#pragma omp parallel for schedule(dynamic, kOpenMpChunk) if (value_count > kOpenMpChunk)
for (int i = 0; i < value_count; i += 1)
{
    output[base + i] = prefix + values[i];
}
```

这里不在并行区内调用 `push_back`，而是提前 `resize`，每个线程只写自己负责的 `output[base + i]`。不同线程写入的位置互不重叠，因此避免了多个线程同时修改 `vector` 内部结构导致的数据竞争。

`total_guesses` 也没有在并行循环里累加，而是在并行函数返回后由主线程一次性执行：

```cpp
total_guesses += value_count;
```

这样避免了对共享计数器做原子操作或 critical 区。

## 对 Generate 的替换

单 segment PT 中，原来的串行循环被替换为：

```cpp
int value_count = pt.max_indices[0];
AppendSegmentValuesOpenMP(guesses, a->ordered_values, value_count);
total_guesses += value_count;
```

多 segment PT 中，前缀生成逻辑保持串行不变，只替换最后一个 segment 的枚举循环：

```cpp
int value_count = pt.max_indices[pt.content.size() - 1];
AppendPrefixedSegmentValuesOpenMP(guesses, guess, a->ordered_values, value_count);
total_guesses += value_count;
```

因此本版本只并行化“给 PT 的最后一个 segment 填充所有 possible value”的部分，优先队列维护、PT 概率计算、训练和哈希流程都保持原样。

## 调度和阈值

OpenMP 使用：

```cpp
schedule(dynamic, kOpenMpChunk)
```

`dynamic` 调度可以缓解不同 value 拼接成本不完全一致时的负载不均衡。`kOpenMpChunk = 256` 用作调度粒度。

同时使用：

```cpp
if (value_count > kOpenMpChunk)
```

当候选 value 数量较少时不启动并行循环，减少 OpenMP 并行区创建和调度开销。

## 编译和线程数

OpenMP 版本需要使用：

```sh
g++ main.cpp train.cpp guessing.cpp md5.cpp -fopenmp -o main
```

线程数由运行时环境变量控制：

```sh
OMP_NUM_THREADS=1
OMP_NUM_THREADS=2
OMP_NUM_THREADS=4
OMP_NUM_THREADS=8
```

本实验服务器 `lscpu` 显示 `CPU(s): 8`，因此基础实验主要比较 1、2、4、8 线程。

## 正确性说明

并行版本保持生成顺序与串行下标顺序一致：第 `i` 个候选 value 仍然写入 `base + i`。因此生成数量应与串行版本一致。实测每次最终输出：

```text
Guesses generated: 10106852
```

与串行版本一致。
