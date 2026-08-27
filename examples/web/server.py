#!/usr/bin/env python3
"""Web 演示前端：浏览器实时查看流式说话人分离与 ASR 转写。

启动（依赖 web extra）:
    uv sync --extra web
    uv run python3 examples/web/server.py --port 8000

浏览器打开 http://localhost:8000：
- 选择回放音频与 ASR 模式，点击启动；
- 服务端逐块喂入管线，事件经 WebSocket 实时推送，前端渲染说话人时间轴与转写文本。

可选参数：
    --host 127.0.0.1  监听地址
    --port 8000       监听端口
    --models-dir models  模型目录（自动探测 VAD/embedding/ASR 模型）
"""
from __future__ import annotations

import argparse
import asyncio
import queue
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sherpa_diarize import (
    Asr,
    OnlineClustering,
    Pipeline,
    SpeakerEmbedder,
    StreamingAsr,
    Vad,
)

ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_WAV = "models/0-four-speakers-zh.wav"
CHUNK_MS = 200
SAMPLE_RATE = 16000
models_dir = ROOT / "models"  # main() 可覆盖

app = FastAPI()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


def _model_paths(models_dir: Path) -> dict:
    """探测可用的模型文件。"""
    out = {
        "vad": str(models_dir / "silero_vad.onnx"),
        "embed": str(models_dir / "wespeaker_zh_cnceleb_resnet34.onnx"),
    }
    paraformer_dir = models_dir / "sherpa-onnx-paraformer-zh-small-2024-03-09"
    streaming_dir = models_dir / "sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13"
    out["asr_offline"] = {
        "model": str(paraformer_dir / "model.int8.onnx"),
        "tokens": str(paraformer_dir / "tokens.txt"),
    }
    out["asr_streaming"] = {
        "model": str(streaming_dir / "ctc-epoch-20-avg-1-chunk-16-left-128.int8.onnx"),
        "tokens": str(streaming_dir / "tokens.txt"),
    }
    out["wav"] = str(models_dir / "0-four-speakers-zh.wav")
    return out


@app.get("/api/models")
async def api_models():
    return _model_paths(models_dir)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    q: queue.Queue = queue.Queue()
    stop = threading.Event()

    async def forward():
        """把工作线程的事件增量推给浏览器。"""
        while True:
            item = await asyncio.to_thread(q.get)  # queue.get 阻塞，转线程执行
            await ws.send_json(item)

    async def control():
        while True:
            msg = await ws.receive_json()
            if msg["type"] == "start":
                stop.clear()
                threading.Thread(
                    target=run_pipeline, args=(msg, q, stop), daemon=True
                ).start()
            elif msg["type"] == "stop":
                stop.set()

    try:
        await asyncio.gather(forward(), control())
    except WebSocketDisconnect:
        stop.set()
    finally:
        stop.set()


def run_pipeline(msg: dict, q: queue.Queue, stop: threading.Event) -> None:
    """工作线程：按块回放音频并推送事件。"""
    models = _model_paths(models_dir)
    wav = msg.get("wav") or models["wav"]
    speed = float(msg.get("speed", 1.0))
    asr_mode = msg.get("asr_mode", "offline")

    try:
        audio, sr = sf.read(wav, dtype="float32", always_2d=True)
        audio = audio[:, 0]
        if sr != SAMPLE_RATE:
            n_out = int(len(audio) * SAMPLE_RATE / sr)
            audio = np.interp(
                np.linspace(0, len(audio) - 1, n_out), np.arange(len(audio)), audio
            ).astype(np.float32)
        total = len(audio) / SAMPLE_RATE
    except Exception as e:  # noqa: BLE001 — 工作线程错误必须上报给前端而非崩溃
        q.put({"type": "error", "message": f"读取音频失败: {e}"})
        return

    asr = None
    streaming = False
    if asr_mode != "none":
        try:
            paths = models["asr_streaming"] if asr_mode == "streaming" else models["asr_offline"]
            if asr_mode == "streaming":
                asr = StreamingAsr(model=paths["model"], tokens=paths["tokens"])
                streaming = True
            else:
                asr = Asr(model=paths["model"], tokens=paths["tokens"])
        except Exception as e:  # noqa: BLE001 — 模型缺失/损坏时上报前端
            q.put({"type": "error", "message": f"加载 ASR 模型失败: {e}"})
            return

    pipe = Pipeline(
        vad=Vad(models["vad"]),
        embedder=SpeakerEmbedder(models["embed"]),
        clustering=OnlineClustering(),
        asr=asr,
        streaming=streaming,
    )

    q.put({"type": "started", "duration": total, "asr_mode": asr_mode})
    chunk = int(CHUNK_MS / 1000 * SAMPLE_RATE)
    n = 0
    for i in range(0, len(audio), chunk):
        if stop.is_set():
            break
        pipe.accept_waveform(audio[i : i + chunk])
        for ev in pipe.events()[n:]:
            q.put({
                "type": "event",
                "start": round(ev.start, 3),
                "end": round(ev.end, 3),
                "speaker": ev.speaker_id,
                "confidence": round(ev.confidence, 3),
                "text": ev.text,
            })
            n += 1
        q.put({"type": "progress", "t": round(min(i / SAMPLE_RATE, total), 2)})
        if speed > 0:
            time.sleep(chunk / SAMPLE_RATE / speed)

    pipe.finish()
    for ev in pipe.events()[n:]:
        q.put({
            "type": "event",
            "start": round(ev.start, 3),
            "end": round(ev.end, 3),
            "speaker": ev.speaker_id,
            "confidence": round(ev.confidence, 3),
            "text": ev.text,
        })
    q.put({"type": "done", "speakers": pipe.clustering.num_speakers})


def main():
    parser = argparse.ArgumentParser(description="sherpa-diarize Web 演示前端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--models-dir", default=str(ROOT / "models"), help="模型目录")
    args = parser.parse_args()

    global models_dir
    models_dir = Path(args.models_dir)
    if not (models_dir / "silero_vad.onnx").is_file():
        raise SystemExit(f"缺少 VAD 模型，请先运行 python3 scripts/download_models.py（--models-dir={models_dir}）")

    print(f"Web 前端: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
