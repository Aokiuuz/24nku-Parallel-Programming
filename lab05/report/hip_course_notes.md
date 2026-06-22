# AMD AUP HIP Programming Course 填空整理


## Lab1 Vector Addition

### 线程索引与 kernel

一维 grid/block 中，全局线程编号为：

```cpp
int idx = blockIdx.x * blockDim.x + threadIdx.x;
```

向量加法 kernel 的核心填空为：

```cpp
__global__ void vector_add(const float* A, const float* B, float* C, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;

    if (idx < N) {
        C[idx] = A[idx] + B[idx];
    }
}
```

每个 GPU 线程负责一个向量元素，`blockIdx.x * blockDim.x + threadIdx.x` 将 block 内局部线程号转换为全局下标。`if (idx < N)` 用于处理总线程数大于元素数时的越界问题。向量加法中各元素之间没有依赖，因此适合 GPU 并行执行。

### 典型计算填空

- `blockIdx.x=0, blockDim.x=256, threadIdx.x=100`，全局下标为 `100`。
- `blockIdx.x=2, blockDim.x=128, threadIdx.x=50`，全局下标为 `306`。
- `blockIdx.x=5, blockDim.x=64, threadIdx.x=0`，全局下标为 `320`。
- `N=1000` 时，block size 为 64、128、256、512 的 grid size 分别为 16、8、4、2，总线程数均为 1024，空闲线程均为 24。
- 多元素每线程版本中，stride 应为 `blockDim.x * gridDim.x`。

host 端基本流程是 `hipMalloc` 申请 device 显存，`hipMemcpy` 在 host 和 device 间复制数据，kernel launch 启动 GPU 线程，`hipDeviceSynchronize` 等待 GPU 完成并暴露异步错误。

## Lab2 Matrix Transpose

### 二维索引与线性内存下标

二维线程组织更适合矩阵任务：

```cpp
int col = blockIdx.x * blockDim.x + threadIdx.x;
int row = blockIdx.y * blockDim.y + threadIdx.y;

if (row < height && col < width) {
    output[col * height + row] = input[row * width + col];
}
```

矩阵以 row-major 方式存在线性内存中，原矩阵元素 `input[row * width + col]` 转置后写到 `output[col * height + row]`。这里输出矩阵的行数是原矩阵列数，列数是原矩阵行数，所以输出下标使用 `height` 作为行跨度。

### 典型计算填空

当 `blockDim=(32,32)`：

- `blockIdx=(0,0), threadIdx=(5,10)` 的全局下标为 `(5,10)`。
- `blockIdx=(1,0), threadIdx=(0,0)` 的全局下标为 `(32,0)`。
- `blockIdx=(2,3), threadIdx=(15,20)` 的全局下标为 `(79,116)`。

对 `rows=100, cols=200` 的矩阵，如果 block 为 `32x32`，需要 `ceil(200/32) x ceil(100/32) = 7 x 4` 个 blocks。

4x6 矩阵的下标示例：

- `(1,0)`：input index 为 `0*6+1=1`，output index 为 `1*4+0=4`。
- `(0,1)`：input index 为 `1*6+0=6`，output index 为 `0*4+1=1`。
- `(3,2)`：input index 为 `2*6+3=15`，output index 为 `3*4+2=14`。

直接转置时，连续线程读取 `input[row * width + col]` 通常是连续地址，但写入 `output[col * height + row]` 会跨行跳跃，导致非合并访存。tiled transpose 使用 shared memory 先按 tile 读入，再交换 block 方向写出，可以改善全局内存访问。`tile[BLOCK_SIZE][BLOCK_SIZE + 1]` 中的 `+1` 用于减少 shared memory bank conflict；`BLOCK_SIZE=32` 时占用 `32 * 33 * 4 = 4224` bytes shared memory。

## Lab3 Histogram

### 原子操作与 shared memory 优化

直方图的核心问题是多个线程可能同时更新同一个 bin，因此必须处理数据竞争。直接 global atomic 的基础版本为：

```cpp
int idx = blockIdx.x * blockDim.x + threadIdx.x;
if (idx < n) {
    int bin = input[idx];
    atomicAdd(&hist[bin], 1);
}
```

全局内存上的 `atomicAdd` 在冲突严重时会被串行化。更好的方案是在每个 block 内用 shared memory 构建局部 histogram，再把 block 级结果合并到 global memory。

### 分析填空

- naive 版本中每个 block 负责一个 bin，并扫描整个输入，所以每个输入元素会被读取 `num_bins` 次。
- 当 `num_bins=256, N=10M` 时，总读取次数为 `2.56B`，若输入为 `int`，仅输入读取就约为 `10.24GB`。
- 优化版本每个输入元素只读一次，理论读取次数下降比例为 `num_bins`，在 256 bins 时为 `256x`。
- shared memory atomic 通常比 global memory atomic 快，因为访问延迟低且作用域限制在 block 内。
- merge 阶段每个 block 对每个 bin 做一次 global atomic，因此每个 bin 的 global atomic 次数等于 block 数。
- grid-stride loop `for (int i = idx; i < N; i += total_threads)` 让固定数量线程覆盖任意长度输入，避免为超大 N 启动过多线程。

## Lab4 Reduction

### shared memory tree reduction

归约把多个元素合并为一个结果，例如求和、最大值或最小值。典型 block 内 tree reduction 为：

```cpp
extern __shared__ float sdata[];

int tid = threadIdx.x;
int i = blockIdx.x * blockDim.x + threadIdx.x;

sdata[tid] = (i < n) ? input[i] : 0.0f;
__syncthreads();

for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) {
        sdata[tid] += sdata[tid + stride];
    }
    __syncthreads();
}

if (tid == 0) {
    partial[blockIdx.x] = sdata[0];
}
```

每一轮 stride 减半，参与写入的线程数也减半。`__syncthreads()` 保证同一 block 内所有线程完成当前轮计算后再进入下一轮。block 间不能用 `__syncthreads()` 同步，因此多 block reduction 需要写出 partial result，再用第二轮 kernel 或 CPU 汇总。

### 分析填空

- 1024 个元素、block size 256 时，每个 block 内需要 `log2(256)=8` 个 reduction steps。
- block 级 reduction 后剩余 `ceil(1024/256)=4` 个 partial sums。
- `N=1,000,000` 时，block size 64 会产生 `ceil(1,000,000/64)=15625` 个最终 atomic 或 partial；block size 1024 会产生 `ceil(1,000,000/1024)=977` 个。
- tree reduction 第一轮之后约一半线程进入空闲。
- warp/wave shuffle 在一个 wavefront 内通过硬件同步执行，不需要 block 级 `__syncthreads()`。
- 每线程处理多个元素可以减少 block 数和最终合并次数，并提高单线程连续访存利用率。

## Lab5 Monte Carlo Integration

### 并行采样思想

Monte Carlo 方法通过大量随机或均匀采样估计积分值。每个采样点之间相互独立，适合让一个线程处理一个或多个采样点，最后再通过 atomic 或 reduction 汇总。

简化伪代码为：

```cpp
int idx = blockIdx.x * blockDim.x + threadIdx.x;
double local = 0.0;

for (int i = idx; i < n_samples; i += blockDim.x * gridDim.x) {
    double x = sample_x(i);
    local += f(x);
}

atomicAdd(result, local);
```

最终结果需要乘以区间长度并除以样本数。性能瓶颈可能来自随机数生成、函数计算和最终归约。

### 分析填空

- atomic reduction 方法对每个线程或每个采样做累加，逻辑工作量为 `O(n_samples)`，但高冲突 atomic 可能导致串行化。
- 使用 shared memory reduction 可先在 block 内求局部和，再让每个 block 只做一次 global atomic。
- 256 threads/block 且 `N=1M` 时，如果每个 block 输出一次 partial，global atomic 数约为 `ceil(1,000,000/256)=3907`；如果固定 256 个 blocks，则 global atomic 为 256 次。
- double precision 通常提供约 15 到 16 位十进制有效数字。若换成 float，超大样本数累加时更容易出现舍入误差。
- grid-stride loop 让 kernel 可以用有限线程处理任意多样本，同时提高每个线程的工作量。

## Lab6 K-Means Clustering

### assignment kernel

K-Means 的两个核心步骤是：把点分配给最近中心，然后更新每个 cluster 的中心。分配阶段天然并行，每个线程处理一个点：

```cpp
int idx = blockIdx.x * blockDim.x + threadIdx.x;
if (idx < num_points) {
    int best_cluster = 0;
    float best_dist = distance(points[idx], centroids[0]);

    for (int c = 1; c < k; c++) {
        float d = distance(points[idx], centroids[c]);
        if (d < best_dist) {
            best_dist = d;
            best_cluster = c;
        }
    }

    labels[idx] = best_cluster;
}
```

每个线程需要计算该点到所有 `k` 个中心的距离，所以单线程复杂度为 `O(k)`。当 `k=100` 时，每个线程执行 100 次距离比较。

### 分析填空

- 更新中心阶段需要把同一 cluster 的点坐标求和并统计数量，会产生写冲突。
- 使用 shared memory atomic 先做 block 内局部累加，再合并到 global memory，可以减少全局原子冲突。
- 如果某个 centroid 没有分配到点，通常保持上一轮中心不变，或按实现策略重新初始化。
- 对 `N=50,000, k=50`，assignment 阶段每点 50 次距离计算，总计 `2,500,000` 次距离计算。
- 若更新阶段每个点对 `x_sum`、`y_sum`、`count` 做 3 次 shared atomic，总 shared atomic 为 `150,000` 次。
- 256 threads/block 时 block 数为 `ceil(50000/256)=196`，若每 block 对每 cluster 写 `x_sum`、`y_sum`、`count`，global atomic 约为 `196 * 50 * 3 = 29,400` 次。
- centroids 被所有线程反复读取，可考虑利用 constant memory、shared memory tiling 或缓存友好的数据布局；当 `k=1000` 时，中心数组更大，cache 压力和每线程计算量都会明显增加。
- K-Means 是迭代算法，每一轮 assignment 依赖上一轮中心，轮与轮之间需要 kernel 完成后的全局同步。
