#!/usr/bin/env python3
"""下载 VAD 与说话人 embedding 模型到 models/ 目录。

用法:
    python3 scripts/download_models.py

默认下载（均为 MIT/Apache 许可、16kHz 可端侧部署的模型）:
- models/silero_vad.onnx                                  VAD（k2-fsa 导出, 629KB）
- models/wespeaker_zh_cnceleb_resnet34.onnx               说话人 embedding（中文）
- models/sherpa-onnx-paraformer-zh-small-2024-03-09/      ASR（中文转写, int8）
- models/0-four-speakers-zh.wav                           demo 音频（4 说话人，中文）

可选:
    python3 scripts/download_models.py --vad-only    # 只下 VAD
    python3 scripts/download_models.py --embed-only  # 只下 embedding
    python3 scripts/download_models.py --asr-only    # 只下 ASR
"""
from __future__ import annotations

import argparse
import os
import ssl
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# (kind, 本地名, 下载 URL, 说明)；kind: "file" 单文件 | "dir" tar.bz2 解压目录
VAD_MODEL = (
    "file",
    "silero_vad.onnx",
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
    "Silero VAD v4（k2-fsa 导出，仅 16kHz，629KB）",
)

EMBEDDING_MODEL = (
    "file",
    "wespeaker_zh_cnceleb_resnet34.onnx",
    ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
     "wespeaker_zh_cnceleb_resnet34.onnx"),
    "WeSpeaker resnet34 说话人 embedding（中文，CNN- Celeb 训练，26.5MB）",
)

ASR_MODEL = (
    "dir",
    "sherpa-onnx-paraformer-zh-small-2024-03-09",
    ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
     "sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2"),
    "Paraformer 中文 ASR（int8，model.int8.onnx + tokens.txt）",
)

DEMO_AUDIO = (
    "file",
    "0-four-speakers-zh.wav",
    ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/"
     "0-four-speakers-zh.wav"),
    "demo 音频：4 个说话人的中文对话",
)


# Python 发行版常缺 CA 证书；探测系统 CA bundle，保证 urllib 可走 HTTPS
_CANDIDATE_CA = [
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/ssl/ca-bundle.pem",
]
_CA_FILE = next((p for p in _CANDIDATE_CA if os.path.isfile(p)), None)


def _https_opener() -> urllib.request.OpenerDirector:
    ctx = ssl.create_default_context(cafile=_CA_FILE) if _CA_FILE else ssl.create_default_context()
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def download(url: str, dest: Path, description: str) -> None:
    if dest.exists():
        print(f"[skip] {dest.name} 已存在")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"[下载] {description}: {url}")
    try:
        with _https_opener().open(url, timeout=300) as resp, open(tmp, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done / total * 100
                    print(f"\r  {done / 1e6:.1f}/{total / 1e6:.1f} MB ({pct:.0f}%)", end="")
        print()
        if dest.suffix == ".tar.bz2":
            import tarfile

            with tarfile.open(tmp, "r:bz2") as tf:
                tf.extractall(dest.parent, filter="data")
            tmp.unlink(missing_ok=True)
        else:
            tmp.replace(dest)
        print(f"[完成] {dest}")
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f"[失败] {url}: {e}", file=sys.stderr)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 sherpa-diarize 所需模型")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--vad-only", action="store_true", help="只下载 VAD 模型")
    group.add_argument("--embed-only", action="store_true", help="只下载 embedding 模型")
    group.add_argument("--asr-only", action="store_true", help="只下载 ASR 模型")
    group.add_argument("--audio-only", action="store_true", help="只下载 demo 音频")
    parser.add_argument(
        "--mirror",
        type=str,
        default="",
        help="GitHub 下载加速前缀，如 https://ghfast.top/（国内网络推荐）",
    )
    args = parser.parse_args()

    prefix = args.mirror
    jobs = []
    if args.vad_only:
        jobs = [VAD_MODEL]
    elif args.embed_only:
        jobs = [EMBEDDING_MODEL]
    elif args.asr_only:
        jobs = [ASR_MODEL]
    elif args.audio_only:
        jobs = [DEMO_AUDIO]
    else:
        jobs = [VAD_MODEL, EMBEDDING_MODEL, ASR_MODEL, DEMO_AUDIO]

    for kind, name, url, desc in jobs:
        download(prefix + url, MODELS_DIR / name, desc)


if __name__ == "__main__":
    main()
