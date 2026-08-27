#!/usr/bin/env python3
"""麦克风实时说话人分离。

依赖: pip install "sherpa-diarize[mic]"（即 sounddevice）
用法:
  python3 examples/diarize_mic.py \
      --vad-model models/silero_vad.onnx \
      --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx
说话时实时打印 "谁在什么时候说话"，Ctrl+C 结束。

同步输出 ASR 转写（可选）：
  python3 examples/diarize_mic.py \
      --vad-model models/silero_vad.onnx \
      --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
      --asr-model models/sherpa-onnx-paraformer-zh-small-2024-03-09/model.int8.onnx \
      --asr-tokens models/sherpa-onnx-paraformer-zh-small-2024-03-09/tokens.txt
"""
from __future__ import annotations

import argparse

from sherpa_diarize import OnlineClustering, Pipeline, SpeakerEmbedder, Vad

try:
    import sounddevice as sd
except (ImportError, OSError) as e:
    raise SystemExit(
        "缺少 sounddevice 或其依赖库 PortAudio。请先: "
        "uv sync --extra mic（Python 包），并在系统安装 libportaudio2（如 apt install libportaudio2）"
    ) from e


def main() -> None:
    parser = argparse.ArgumentParser(description="麦克风实时流式说话人分离")
    parser.add_argument("--vad-model", required=True, help="silero_vad.onnx 路径")
    parser.add_argument("--embed-model", required=True, help="说话人 embedding onnx 路径")
    parser.add_argument("--asr-model", type=str, default="", help="ASR onnx 路径（可选）")
    parser.add_argument("--asr-tokens", type=str, default="", help="ASR tokens.txt 路径（--asr-model 提供时必填）")
    parser.add_argument("--threshold", type=float, default=0.6, help="说话人归并阈值")
    parser.add_argument("--merge-threshold", type=float, default=0.9, help="质心合并阈值")
    parser.add_argument("--device", type=int, default=None, help="输入设备索引（默认系统默认设备）")
    args = parser.parse_args()

    if bool(args.asr_model) != bool(args.asr_tokens):
        parser.error("--asr-model 与 --asr-tokens 必须同时提供")

    asr = None
    if args.asr_model:
        from sherpa_diarize import Asr

        asr = Asr(model=args.asr_model, tokens=args.asr_tokens)

    pipe = Pipeline(
        vad=Vad(args.vad_model),
        embedder=SpeakerEmbedder(args.embed_model),
        clustering=OnlineClustering(
            threshold=args.threshold, merge_threshold=args.merge_threshold
        ),
        asr=asr,
    )

    def show(ev):
        line = f"[{ev.start:7.2f}s - {ev.end:7.2f}s] speaker_{ev.speaker_id} (conf {ev.confidence:.2f})"
        if ev.text:
            line += f"\n            {ev.text}"
        print(line)

    chunk_ms = 100
    chunk = int(chunk_ms / 1000 * 16000)
    n = 0
    print("开始监听，请说话（Ctrl+C 结束）")
    try:
        with sd.InputStream(
            device=args.device, channels=1, samplerate=16000, dtype="float32"
        ) as stream:
            while True:
                samples, _ = stream.read(chunk)  # 阻塞读 100ms
                pipe.accept_waveform(samples.reshape(-1))
                for ev in pipe.events()[n:]:
                    show(ev)
                    n += 1
    except KeyboardInterrupt:
        pipe.finish()
        for ev in pipe.events()[n:]:
            show(ev)
        print(f"\n结束，共识别 {pipe.clustering.num_speakers} 个说话人")


if __name__ == "__main__":
    main()
