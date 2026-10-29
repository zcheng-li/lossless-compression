# 实验数据与绘图

在项目根目录运行以下两条命令。脚本包含依赖声明，`uv` 会准备相应环境；
这里指定作业环境的 Python 3.12.4，不使用系统默认的 Python。

```bash
uv run --python 3.12.4 experiments/run_experiments.py
uv run --python 3.12.4 experiments/plot_experiments.py
```

完整采集会逐组重新压缩，并对每组独立解码 3 次。所有实验按顺序执行。
编码时间仅记录为墙钟时间；报告使用的解码时间是 `/usr/bin/time -p`
给出的 user CPU time 的中位数，同时保存每次测量以及最小值、最大值。
每次解码均运行计入体积的同一个 `.pyc`，并逐字节比较原文件。

## 实验范围

- 阶数：最终调权、UE、4 字节文件头不变，测试 K=4、5、6。
- ESCAPE 权重：固定 K=5、symbol factor=200，测试
  beta=110、100、95、90、88、87、86、85、80。
- 逐项改进：PPM-C、标准 PPM-D、2c 修改、增加 UE、调权、精简文件头和解码器。
  前五组使用同一个 13 字节格式及通用解码器模板；最后一组使用原始 FT 版本。
- 算法比较：项目内的双字节 Huffman、静态 arithmetic、LZ78、LZW 与最终 FT 方法。

默认共 20 个独立配置。K=5、beta=86 的最终配置在各实验组中复用。
可以先查看计划，不运行实验：

```bash
python3 experiments/run_experiments.py --list
```

生成的 PPM 变体会同时修改编码器与解码器的权重、阶数和更新规则。
标准 PPM-D 会明确恢复为 `2*c-1`，不会直接把当前 `PPMD+arithmetic`
目录中的 `2*c` 实现误标为标准 PPM-D。
最终 K=5、beta=86 配置直接复制当前 FT 源码，保留其真实解码器体积。
脚本还会检查通用格式与精简格式的 arithmetic payload 相同，文件头仅差 9 字节。
原有编解码器、`compressed`、提交目录和 LaTeX 文件均不修改。

## 保存的数据

默认输出到 `experiments/results/`：

- `metadata.json`：系统、CPU、Python、minifier 版本、输入 SHA-256、源码 SHA-256 和测量设置。
- `results.json`：完整结果、每次计时、精简格式的 payload 一致性检查。
- `results.csv`：所有独立配置；失败组有错误信息，未成功测得的指标留空。
- `order.csv`、`weights.csv`、`design.csv`、`algorithms.csv`：对应报告各表。
- `sources/`：实验使用的源码快照。
- `cases/<配置>/`：该组生成的完整源码、压缩数据、minified decoder、`.pyc`、还原文件和日志。
- `figures/`：运行绘图脚本后生成的图片和 `plot_manifest.json`。

CSV 中 `total_ratio_percent` 对应 `(compressed_bytes + decoder_pyc_bytes) / original_bytes * 100`。
`status=verified` 表示所有指定的解码重复均通过逐字节验证；它不自动代表满足全部作业约束。
`allowed_imports_only` 单独记录是否只使用 `struct`/`decimal`，
`user_cpu_limit_met` 单独记录每次 user CPU time 是否均不超过 1200 秒。
当前静态 arithmetic 基线导入 `bisect`，因此会标记为额外导入的参考实现，图中加星号。
这里保留其现有实现，不会静默替换它的算法或改变计时含义。

## 中断与继续

中断后再次运行同一条采集命令，会校验已完成组的文件 SHA-256 并复用结果。
失败或中断的组会重跑。每完成一组就更新 JSON 和 CSV。
使用不同组时，已保存的其他组仍保留，例如可只先采集参数组：

```bash
uv run --python 3.12.4 experiments/run_experiments.py --groups order weights
```

输入、源码、机器、Python/minifier 版本、重复次数或超时设置改变时，
请用 `--output` 指定新的结果目录，避免混用不可比较的数据。
若使用新目录绘图，用 `--results 新目录/results.json`。
`--force` 可在条件不变时重新测量已完成组。
单次子进程的默认墙钟超时是 1800 秒，可用 `--timeout` 设置。

## 图片

绘图脚本只使用验证成功的数据，不会把缺失或失败结果当成零。
未完成的实验组会在图题中注明已验证数量。输出四组 PDF/PNG：

- `context_order`：阶数与压缩大小。
- `escape_weight`：相对 ESCAPE 权重与压缩大小。
- `design_comparison`：各改进阶段的压缩数据及解码器大小。
- `algorithm_comparison`：其他算法的总比例、解码 CPU 时间及重复测量范围。

参数图分别标注当前提交参数和本次实测最优点，不预设实测最优一定是 K=5 或 beta=86。
PDF 为可供 LaTeX 使用的矢量图，PNG 为 300 dpi 预览。
脚本不会自动填报告表格或插图，便于先核对数据再决定如何报告。
