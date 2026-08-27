# sherpa-diarize

On-Device Real-time Streaming Speaker Diarization based on [Sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).

端侧实时流式说话人分离（"谁在什么时候说话"），构建于 sherpa-onnx 之上，纯 CPU / 端侧可跑。

## 目标

- **实时流式**：按音频块（chunk）增量处理，说话人切换事件低延迟产出，不依赖整段录音。
- **端侧部署**：基于 sherpa-onnx（ONNX Runtime），无需 GPU / 云端服务。
- **即插即用**：文件回放模拟 + 麦克风实时输入两种运行方式。

## 核心思路

sherpa-onnx 提供 VAD 与说话人 embedding 能力；本项目在其构件之上搭建流式管线：

1. **流式 VAD**（Silero VAD）把音频流切成说话片段（turn），长句内部再做说话人变化检测（能量静音候选 + 两侧 embedding 确认），解决两人快速交替时混合成一个 turn 的问题。
2. **说话人 embedding**（WeSpeaker / 3D-Speaker）对每个 turn 提取定长向量（L2 归一化）。
3. **在线聚类 / 说话人跟踪**：维护每名说话人的质心（EMA 更新），余弦相似度超过阈值则归入已有说话人，否则新建说话人；周期性合并相似质心，修复过分割。
4. **ASR 转写**（可选）：对每个 turn 用 Paraformer 离线识别同步输出转写文本。
5. 输出说话人 turn 事件：`(start, end, speaker_id, confidence, text)`，可导出 RTTM。

## 快速开始

### 1. 安装依赖

```bash
uv sync                    # 核心依赖（sherpa-onnx + numpy + soundfile）
uv sync --extra mic        # 需要麦克风输入时
```

### 2. 下载模型

```bash
python3 scripts/download_models.py                # 海外网络
python3 scripts/download_models.py --mirror https://ghfast.top/   # 国内网络加速
```

默认下载到 `models/`：

| 文件 | 用途 | 大小 |
| --- | --- | --- |
| `silero_vad.onnx` | Silero VAD v4（16kHz） | 629 KB |
| `wespeaker_zh_cnceleb_resnet34.onnx` | 说话人 embedding（中文） | 26.5 MB |
| `sherpa-onnx-paraformer-zh-small-2024-03-09/` | Paraformer 中文 ASR（int8，可选） | ~80 MB |
| `0-four-speakers-zh.wav` | demo 音频（4 说话人中文对话） | 1.8 MB |

可选：`--vad-only` / `--embed-only` / `--asr-only` / `--audio-only` 只下载部分文件。

### 3. 运行示例

文件回放（按 200ms 块模拟实时流）：

```bash
python3 examples/diarize_file.py \
    --wav models/0-four-speakers-zh.wav \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx
```

同步输出 ASR 转写（可选）：

```bash
python3 examples/diarize_file.py \
    --wav models/0-four-speakers-zh.wav \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
    --asr-model models/sherpa-onnx-paraformer-zh-small-2024-03-09/model.int8.onnx \
    --asr-tokens models/sherpa-onnx-paraformer-zh-small-2024-03-09/tokens.txt
```

麦克风实时（需 `uv sync --extra mic`）：

```bash
python3 examples/diarize_mic.py \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
    --asr-model models/sherpa-onnx-paraformer-zh-small-2024-03-09/model.int8.onnx \
    --asr-tokens models/sherpa-onnx-paraformer-zh-small-2024-03-09/tokens.txt
```

### 4. 示例输出

```
[   4.49s -    6.57s] speaker_0 (conf 0.83)
            下面我们来播放一些测试音
[   6.57s -   13.67s] speaker_1 (conf 0.36)
            非常累的时候就会站在阳台上吹吹风看远处的灯火明明暗暗
[  13.67s -   16.84s] speaker_2 (conf 0.21)
            和你们一起走过很多很多的路坚持到
[  22.18s -   24.74s] speaker_0 (conf 0.86)
            我们下面播放一条雷军的测试音频
...
共 10 个 turn, 4 个说话人
```

demo 音频的真实说话人数为 4，与输出一致；与 sherpa-onnx 离线 diarization（pyannote 分割 + threshold 0.7）逐段对应，边界误差 ≤ 0.3s。

导出 RTTM：

```bash
python3 examples/diarize_file.py ... --rttm out.rttm
```

### 5. 参数说明

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--threshold` | 0.6 | 说话人归并阈值；越大越倾向新建说话人 |
| `--merge-threshold` | 0.9 | 周期性质心合并阈值 |
| `--max-turn` | 6.0 | 超过该时长的 turn 内部做说话人变化检测（秒） |
| `--change-threshold` | 0.6 | 长 turn 内确认说话人切换的相似度阈值 |
| `--chunk-ms` | 200 | 喂入块时长（文件回放） |
| `--realtime` | off | 文件按真实时间速度回放 |
| `--asr-model` / `--asr-tokens` | 空 | 启用 ASR 转写（两个需同时提供） |

## 目录结构

```
sherpa-diarize/
├── sherpa_diarize/          # 核心包
│   ├── vad.py               # 流式 VAD 封装（turn 切分）
│   ├── embedding.py         # 说话人 embedding 提取封装
│   ├── clustering.py        # 在线聚类（质心跟踪 + 周期合并）
│   ├── asr.py               # ASR 转写封装（Paraformer，可选）
│   └── pipeline.py          # 流式管线（含长 turn 说话人变化检测、静音 trim、RTTM 导出）
├── scripts/
│   └── download_models.py   # 下载 VAD / embedding 模型与 demo 音频
├── examples/
│   ├── diarize_file.py      # 文件回放（实时模拟）
│   └── diarize_mic.py       # 麦克风实时
├── tests/                   # 单元测试（聚类逻辑、trim、长 turn 切分）
└── pyproject.toml           # uv 工程
```

## 测试

```bash
uv run pytest tests/ -q
```

## 端侧（Android）规划

本项目为端侧部署的 Python 演示版，最终目标是在 Android 上以原生代码运行：

- sherpa-onnx 官方提供 Android 示例（VAD、实时 ASR）与预编译 APK，见
  <https://k2-fsa.github.io/sherpa/onnx/vad/silero-vad.html#android-examples>；
- 迁移路径：`Vad`/`SpeakerEmbedder` 直接对应 sherpa-onnx 的 C API
  （`VoiceActivityDetector`、`SpeakerEmbeddingExtractor`），
  管线中的聚类/trim/变化检测为纯数值逻辑，可平移为 C++/JNI；
- 模型文件（`silero_vad.onnx` + `wespeaker_zh_cnceleb_resnet34.onnx`）可直接打包进 APK assets。

## 依赖

- sherpa-onnx（ONNX Runtime 运行时，`sherpa-onnx-bin` 提供 `libonnxruntime.so`）
- numpy
- soundfile（音频文件读取）
- 可选：sounddevice（麦克风输入）
