# sherpa-diarize

On-Device Real-time Streaming Speaker Diarization based on [Sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).

端侧实时流式说话人分离（"谁在什么时候说话"），构建于 sherpa-onnx 之上，纯 CPU / 端侧可跑。

## 目标

- **实时流式**：按音频块（chunk）增量处理，说话人切换事件低延迟产出，不依赖整段录音。
- **端侧部署**：基于 sherpa-onnx（ONNX Runtime），无需 GPU / 云端服务。
- **即插即用**：文件回放模拟 + 麦克风实时输入两种运行方式。

## 核心思路

sherpa-onnx 提供离线整段 diarization 能力；本项目在其构件之上搭建流式管线：

1. **流式 VAD**（Silero VAD）把音频流切成说话片段（turn），长句按最大时长拆分以限制延迟。
2. **说话人 embedding**（3D-Speaker / WeSpeaker）对每个 turn 提取定长向量。
3. **在线聚类 / 说话人跟踪**：维护每名说话人的质心（均值 embedding），余弦相似度超过阈值则归入已有说话人并更新质心，否则新建说话人；周期性重聚类以合并过分割片段。
4. 输出说话人 turn 事件：`(start, end, speaker_id, confidence)`，可导出 RTTM / JSON。

## 目录结构（规划）

```
sherpa-diarize/
├── sherpa_diarize/          # 核心包
│   ├── vad.py               # 流式 VAD 封装
│   ├── embedding.py         # 说话人 embedding 提取封装
│   ├── clustering.py        # 在线聚类（质心跟踪 + 增量 AHC）
│   └── pipeline.py          # 流式 diarization 管线
├── scripts/
│   └── download_models.py   # 下载 VAD / embedding 模型
├── examples/
│   ├── diarize_file.py      # 文件回放（实时模拟）
│   └── diarize_mic.py       # 麦克风实时
└── pyproject.toml           # uv 工程
```

## 快速开始

（待补充：模型下载、依赖安装、运行示例）

## 依赖

- sherpa-onnx（ONNX Runtime 运行时）
- numpy
- 可选：sounddevice（麦克风输入）、soundfile（音频文件读取）
