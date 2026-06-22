# AUP 真实 PCFG 端到端实验运行指南

## 1. 启动 GPU 服务器

在 AUP Learning Cloud 的 **Launch Your Server** 页面选择：

- Resource：`Development Environment` → `VSCode Server GPU`
- GPU Node：`AMD Radeon 8060S (Strix Halo iGPU)`
- Runtime：建议 `120 minutes`；配额不足时至少选择 `60 minutes`
- Git Repository：留空

点击 **Launch Server**。服务器进入开发环境后再上传文件，计费时间从服务器启动后开始计算。

## 2. 上传并解压实验包

将 `PCFG_GPU_real.zip` 上传到 `~/my_work`。在终端执行：

```bash
cd ~/my_work
rm -rf pcfg_real
unzip -q PCFG_GPU_real.zip -d pcfg_real
cd pcfg_real
find . -maxdepth 4 -type f | sort
```

列表中应包含 `Makefile`、`run_real.sh`、`src/gpu`、`pcfg_gpu/guess_mpi_advanced` 和 `scripts`。

## 3. 确认训练数据

先检查平台数据集：

```bash
test -r /guessdata/Rockyou-singleLined-full.txt \
  && echo "dataset ready" \
  || echo "dataset missing"
wc -l /guessdata/Rockyou-singleLined-full.txt 2>/dev/null || true
```

显示 `dataset ready` 时直接进入第 4 节。运行脚本会优先使用该文件，并在环境记录中保存文件行数、字节数和 SHA-256 校验和。

### 平台缺少 `/guessdata` 时

在能够访问该数据集的 ARM 环境中执行：

```bash
head -n 1000000 /guessdata/Rockyou-singleLined-full.txt > Rockyou-1m.txt
wc -l Rockyou-1m.txt
sha256sum Rockyou-1m.txt
```

确认行数为 `1000000`，下载 `Rockyou-1m.txt`，再上传到 AUP 的 `~/my_work/pcfg_real/data/`。AUP 中执行：

```bash
cd ~/my_work/pcfg_real
wc -l data/Rockyou-1m.txt
sha256sum data/Rockyou-1m.txt
```

运行脚本会在平台数据集缺失时自动使用 `data/Rockyou-1m.txt`。也可以显式指定其他可读文件：

```bash
TRAIN_PATH=/absolute/path/to/training.txt bash run_real.sh
```

## 4. 运行完整实验

执行：

```bash
cd ~/my_work/pcfg_real
bash run_real.sh
```

脚本按以下顺序运行：

1. 记录主机、ROCm、GPU 和训练数据环境；
2. 编译合成 PT 回归程序和真实 PCFG 端到端程序；
3. 执行单 PT、多 PT、overlap 和 schedule 合成回归测试；
4. 训练真实 PCFG 模型并收集一组共享 `WorkUnit`；
5. 在 10K、100K 和 1M 候选规模下运行六种模式，每种重复 5 次；
6. 校验候选数量、顺序或排序后集合、FNV 哈希及 CPU/GPU 分流守恒；
7. 生成原始 CSV、汇总 CSV、验证记录和可视化图表。

终端持续输出 `Training...`、`[real-bench]` 等内容属于正常运行。看到以下两行且终端提示符重新出现时，完整实验结束：

```text
Real PCFG experiment complete.
Validation: results/real_validation.txt
```

## 5. 验收结果

执行：

```bash
cd ~/my_work/pcfg_real
cat results/real_validation.txt
grep -c '^\[real-bench\]' results/real_raw.txt
grep -c 'correctness=PASS' results/real_raw.txt
grep -E 'correctness=FAIL|HIP error|\[error\]|make: \*\*\*' \
  results/real_raw.txt results/real_build.log results/real_synthetic_regression.txt || true
```

完整结果应满足：

- `status=PASS`
- `benchmark_rows=90`
- `[real-bench]` 行数为 `90`
- `correctness=PASS` 行数为 `90`
- 最后一条错误检索命令无输出

同时检查关键文件：

```bash
ls -lh results/real_*.txt results/real_*.csv
find results/figures -maxdepth 1 -type f -printf '%f\n' 2>/dev/null | sort
column -s, -t < results/real_summary.csv | head -n 20
```

若平台未安装 Matplotlib、Pandas 或 Seaborn，脚本会保留完整且已验证的 CSV，并显示绘图依赖警告；这不会影响实验数据验收，图表可在下载后生成。

## 6. 打包并下载

确认实验进程结束后执行：

```bash
cd ~/my_work/pcfg_real
tar -czf ../PCFG_GPU_real_completed.tar.gz \
  Makefile run_real.sh RUN_GUIDE.md src pcfg_gpu scripts results
cd ..
echo $?
ls -lh PCFG_GPU_real_completed.tar.gz
tar -tzf PCFG_GPU_real_completed.tar.gz | grep -E \
  'real_(raw|summary|validation|environment)\.(txt|csv)$'
```

`echo $?` 应为 `0`。在左侧文件栏中刷新 `~/my_work`，右键 `PCFG_GPU_real_completed.tar.gz` 并选择 **Download**。

本地建议保存到：

```text
D:\26Spring\并行程序设计\lab\lab05\PCFG_GPU_real_completed.tar.gz
```

## 7. 停止服务器

下载完成并确认压缩包大小正常后，返回 AUP 控制页，点击 **Stop Server** 或 **Delete Server**。关闭浏览器标签不会立即释放 GPU 配额。
