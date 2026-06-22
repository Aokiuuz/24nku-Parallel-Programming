# guess-pthread 相对 guess-serial 的修改说明

## 修改范围

本版本只修改了 `guessing.cpp` 中 PCFG 口令生成阶段，没有改动训练、MD5 哈希、`main.cpp` 的哈希与清理流程。

串行版本的主要瓶颈在 `PriorityQueue::Generate(PT pt)` 中的两个循环：

1. 单 segment PT：遍历该 segment 的全部 `ordered_values`，逐个生成口令。
2. 多 segment PT：先串行生成最后一个 segment 之前的前缀，再遍历最后一个 segment 的全部 `ordered_values`，逐个生成 `prefix + value`。

每个 value 对应一个独立口令，循环迭代之间没有依赖，因此可以用 Pthread 对这些 value 做区间划分。

## 新增头文件

相对串行版本，文件开头增加：

```cpp
#include <cstdlib>
#include <pthread.h>
```

其中 `<cstdlib>` 用于读取和转换环境变量，`<pthread.h>` 用于 `pthread_create` 和 `pthread_join`。

## 新增辅助结构和函数

在匿名命名空间中新增：

```cpp
const int kPthreadMinWorkPerThread = 256;

struct GenerateTask
{
    int begin;
    int end;
    size_t base;
    const string *prefix;
    const vector<string> *values;
    vector<string> *output;
};
```

`GenerateTask` 是传给每个线程的参数结构，包含：

- `begin/end`：当前线程负责的 value 下标区间。
- `base`：本次追加结果在 `guesses` 中的起始位置。
- `prefix`：多 segment PT 已经确定的前缀；单 segment PT 使用空前缀。
- `values`：最后一个 segment 的候选 value 列表。
- `output`：最终写入的 `guesses`。

新增线程数读取函数：

```cpp
int ReadThreadCountFromEnv();
int GetWorkerCount(int value_count);
```

`ReadThreadCountFromEnv` 依次读取：

```text
PCFG_THREADS
PTHREAD_NUM_THREADS
THREAD_NUM
```

如果没有设置，则默认使用 4 线程。`GetWorkerCount` 会把线程数限制在 1 到 8 之间，并且不会超过本次 `value_count`。限制到 8 是因为实验节点 `lscpu` 显示 `CPU(s): 8`。

新增 worker 函数：

```cpp
void *GenerateWorker(void *arg);
```

该函数根据 `GenerateTask` 中的 `[begin, end)` 区间生成口令。如果 `prefix` 为空，直接写入 `values[i]`；否则写入 `prefix + values[i]`。

新增总入口函数：

```cpp
void AppendSegmentValuesPthread(vector<string> &output,
                                const string &prefix,
                                const vector<string> &values,
                                int value_count);
```

它负责扩展结果数组、划分任务区间、创建线程并等待所有线程结束。

## 并行实现方式

串行版本在循环中直接执行：

```cpp
guesses.emplace_back(temp);
total_guesses += 1;
```

Pthread 版本改为先扩展 `guesses`：

```cpp
const size_t base = output.size();
output.resize(base + value_count);
```

然后把 `[0, value_count)` 按块划分给多个线程：

```cpp
int block = (value_count + thread_count - 1) / thread_count;
```

每个线程只写自己负责的下标：

```cpp
output[task->base + i] = prefix + values[i];
```

这样不在多线程中执行 `push_back`，避免了多个线程同时修改同一个 `vector` 内部结构导致的数据竞争。所有线程只读 `prefix` 和 `values`，并写入互不重叠的 `output` 下标。

`total_guesses` 也没有在线程中累加，而是在所有线程完成后由主线程执行：

```cpp
total_guesses += value_count;
```

因此不需要对计数器使用 mutex 或 atomic。

## 线程创建和同步

当任务量较小时：

```cpp
if (thread_count == 1 || value_count < kPthreadMinWorkPerThread)
```

直接调用 `GenerateWorker` 串行执行，避免频繁创建线程的额外开销。

当任务量足够大时，使用：

```cpp
pthread_create(&threads[tid], nullptr, GenerateWorker, &tasks[tid]);
```

为每个任务区间创建线程，之后使用：

```cpp
pthread_join(threads[tid], nullptr);
```

等待所有线程完成。这里的同步点保证在 `AppendSegmentValuesPthread` 返回时，`guesses` 中本次生成的所有口令已经写入完毕。

## 对 Generate 的替换

单 segment PT 中，原来的串行循环被替换为：

```cpp
int value_count = pt.max_indices[0];
const string empty_prefix;
AppendSegmentValuesPthread(guesses, empty_prefix, a->ordered_values, value_count);
total_guesses += value_count;
```

多 segment PT 中，前缀生成逻辑保持不变，只替换最后一个 segment 的枚举循环：

```cpp
int value_count = pt.max_indices[pt.content.size() - 1];
AppendSegmentValuesPthread(guesses, guess, a->ordered_values, value_count);
total_guesses += value_count;
```

因此本版本只并行化“给 PT 的最后一个 segment 填充所有 possible value”的部分，优先队列维护、PT 概率计算、训练和哈希流程都保持原样。

## 编译和线程数

Pthread 版本需要使用：

```sh
g++ main.cpp train.cpp guessing.cpp md5.cpp -pthread -o main
```

线程数通过环境变量传入，例如：

```sh
PCFG_THREADS=1
PCFG_THREADS=2
PCFG_THREADS=4
PCFG_THREADS=8
```

当前代码会把大于 8 的线程数截断为 8。已有 `T16` 结果只表示提交时传入了 16，但程序实际最多使用 8 个 worker，整理数据时不应把它作为真实 16 线程结果。

## 正确性说明

并行版本保持生成下标和串行枚举下标一致：第 `i` 个候选 value 写入 `base + i`。因此输出数量应与串行版本一致。实测每次最终输出：

```text
Guesses generated: 10106852
```

与串行版本一致。
