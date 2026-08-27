#!/usr/bin/env python3
"""文件回放模拟实时流式说话人分离。

按块（默认 200ms）把 wav 增量喂入管线，模拟实时输入：
  python3 examples/diarize_file.py --wav models/0-four-speakers-zh.wav \
      --vad-model models/silero_vad.onnx \
      --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx

常用参数：
  --chunk-ms 200      每块时长（越小越"实时"，越大越快）
  --realtime          按真实时间速度回放（默认尽快跑完）
  --threshold 0.6     说话人归并阈值
  --rttm out.rttm     导出 RTTM 标注文件
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from sherpa_diarize import OnlineClustering, Pipeline, SpeakerEmbedder, Vad


def resample_to_16k(audio: np.ndarray, src_rate: int) -> np.ndarray:
    """线性插值重采样到 16kHz（演示用；端侧由采集端保证 16k）。"""
    if src_rate == 16000:
        return audio
    n_out = int(len(audio) * 16000 / src_rate)
    x = np.linspace(0, len(audio) - 1, n_out)
    return np.interp(x, np.arange(len(audio)), audio).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description="文件回放实时流式说话人分离")
    parser.add_argument("--wav", required=True, help="输入 wav（16kHz 单声道最佳，其他采样率自动重采样）")
    parser.add_argument("--vad-model", required=True, help="silero_vad.onnx 路径")
    parser.add_argument("--embed-model", required=True, help="说话人 embedding onnx 路径")
    parser.add_argument("--chunk-ms", type=int, default=200, help="喂入块时长（毫秒）")
    parser.add_argument("--realtime", action="store_true", help="按真实时间速度回放")
    parser.add_argument("--threshold", type=float, default=0.6, help="说话人归并阈值")
    parser.add_argument("--merge-threshold", type=float, default=0.9, help="质心合并阈值")
    parser.add_argument("--max-turn", type=float, default=6.0, help="超过该时长的 turn 内部做说话人变化检测")
    parser.add_argument("--change-threshold", type=float, default=0.6, help="长 turn 内说话人切换的相似度阈值")
    parser.add_argument("--rttm", type=str, default="", help="导出 RTTM 文件路径（可选）")
    args = parser.parse_args()

    audio, sr = sf.read(args.wav, dtype="float32", always_2d=True)
    audio = audio[:, 0]  # 单声道
    audio = resample_to_16k(audio, sr)
    print(f"音频: {len(audio) / 16000:.1f}s @16kHz, 块 {args.chunk_ms}ms")

    pipe = Pipeline(
        vad=Vad(args.vad_model),
        embedder=SpeakerEmbedder(args.embed_model),
        clustering=OnlineClustering(
            threshold=args.threshold, merge_threshold=args.merge_threshold
        ),
        max_turn_seconds=args.max_turn,
        change_threshold=args.change_threshold,
    )

    chunk = int(args.chunk_ms / 1000 * 16000)
    chunk_sec = chunk / 16000
    n = 0
    for i in range(0, len(audio), chunk):
        pipe.accept_waveform(audio[i : i + chunk])
        for ev in pipe.events()[n:]:
            print(f"[{ev.start:7.2f}s - {ev.end:7.2f}s] speaker_{ev.speaker_id} (conf {ev.confidence:.2f})")
            n += 1
        if args.realtime:
            time.sleep(chunk_sec)

    pipe.finish()
    for ev in pipe.events()[n:]:
        print(f"[{ev.start:7.2f}s - {ev.end:7.2f}s] speaker_{ev.speaker_id} (conf {ev.confidence:.2f})")

    events = pipe.events()
    durations = {}
    for ev in events:
        durations[ev.speaker_id] = durations.get(ev.speaker_id, 0.0) + (ev.end - ev.start)
    print("\n说话人统计:")
    for sid, dur in sorted(durations.items()):
        print(f"  speaker_{sid}: {dur:.2f}s")
    print(f"共 {len(events)} 个 turn, {pipe.clustering.num_speakers} 个说话人")

    if args.rttm:
        Path(args.rttm).write_text(pipe.to_rttm(Path(args.wav).stem))
        print(f"RTTM 已写入 {args.rttm}")


if __name__ == "__main__":
    main()
