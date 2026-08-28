#!/usr/bin/env python3
"""Web 前端后端：浏览器音频（示例/上传/录音）经 WebSocket 二进制通道喂入管线。

协议（/ws，文本消息为 JSON，其余为 Float32 16kHz 音频块）：
  客户端 → 服务端:
    {type:"config", asr_mode:"none"|"offline"|"streaming"}   开始前配置（每连接一次）
    <二进制 Float32 块>                                      音频（100ms=3200 样本）
    {type:"end"}                                             音频结束（pipeline.finish）
    {type:"stop"}                                            中断
  服务端 → 客户端:
    {type:"started"}                                         管线就绪
    {type:"partial", text}                                   流式增量识别文本（灰色预览）
    {type:"event", start, end, speaker, confidence, text}    说话人 turn 事件（final）
    {type:"progress", t}                                     累计音频秒数
    {type:"done", speakers}                                  处理完成
    {type:"error", message}                                  错误

启动:
    uv sync --extra web
    uv run python3 examples/web/server.py --port 8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
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
SAMPLE_RATE = 16000
models_dir = ROOT / "models"  # main() 可覆盖
WEBUI_DIST = ROOT / "webui" / "dist"

app = FastAPI()
app.mount("/models", StaticFiles(directory=models_dir), name="models")

if WEBUI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEBUI_DIST / "assets"), name="assets")
    index_file = WEBUI_DIST / "index.html"
else:
    index_file = None  # 前端未构建：根路径返回提示


@app.get("/")
async def index():
    if index_file is None:
        return HTMLResponse(
            "<h2>前端未构建</h2><p>请先执行: cd webui && npm install && npm run build，然后刷新本页。</p>",
            status_code=503,
        )
    return FileResponse(index_file)


def _model_paths() -> dict:
    """探测可用的模型文件。"""
    paraformer_dir = models_dir / "sherpa-onnx-paraformer-zh-small-2024-03-09"
    streaming_dir = models_dir / "sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13"
    return {
        "vad": models_dir / "silero_vad.onnx",
        "embed": models_dir / "wespeaker_zh_cnceleb_resnet34.onnx",
        "asr_offline": {
            "model": paraformer_dir / "model.int8.onnx",
            "tokens": paraformer_dir / "tokens.txt",
        },
        "asr_streaming": {
            "model": streaming_dir / "ctc-epoch-20-avg-1-chunk-16-left-128.int8.onnx",
            "tokens": streaming_dir / "tokens.txt",
        },
        "demo_wavs": {
            "0-four-speakers-zh.wav": "/models/0-four-speakers-zh.wav",
        },
    }


@app.get("/api/models")
async def api_models():
    m = _model_paths()
    return {
        "models_ready": all(p.is_file() for p in [m["vad"], m["embed"]]),
        "asr_offline_ready": all(p.is_file() for p in m["asr_offline"].values()),
        "asr_streaming_ready": all(p.is_file() for p in m["asr_streaming"].values()),
        "demo_wavs": m["demo_wavs"],
    }


def build_pipeline(asr_mode: str, outq: asyncio.Queue, stop) -> Pipeline:
    """构造管线。模型缺失时抛异常（由调用方转为 error 消息）。"""
    m = _model_paths()
    asr = None
    streaming = False
    if asr_mode != "none":
        if asr_mode == "streaming":
            asr = StreamingAsr(model=str(m["asr_streaming"]["model"]), tokens=str(m["asr_streaming"]["tokens"]))
            streaming = True
        else:
            asr = Asr(model=str(m["asr_offline"]["model"]), tokens=str(m["asr_offline"]["tokens"]))
    return Pipeline(
        vad=Vad(str(m["vad"])),
        embedder=SpeakerEmbedder(str(m["embed"])),
        clustering=OnlineClustering(),
        asr=asr,
        streaming=streaming,
    )


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    outq: asyncio.Queue = asyncio.Queue()
    pipe: Pipeline | None = None
    total_seconds = 0.0
    n_events = 0

    async def sender():
        try:
            while True:
                msg = await outq.get()
                await ws.send_json(msg)
        except Exception:  # noqa: S110, BLE001 — 连接断开时 send 失败，任务退出即可
            pass

    sender_task = asyncio.create_task(sender())
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break  # 客户端断开，不能再调用 receive()
            if msg.get("type") != "websocket.receive":
                continue
            if "text" in msg:
                data = json.loads(msg["text"])
                if data["type"] == "config":
                    try:
                        pipe = build_pipeline(data.get("asr_mode", "none"), outq, None)
                    except Exception as e:  # noqa: BLE001 — 模型缺失/损坏上报前端
                        await outq.put({"type": "error", "message": f"模型加载失败: {e}"})
                        pipe = None
                    else:
                        total_seconds = 0.0
                        n_events = 0
                        await outq.put({"type": "started", "asr_mode": data.get("asr_mode", "none")})
                elif data["type"] == "end":
                    if pipe is not None:
                        pipe.finish()
                        speakers = pipe.clustering.num_speakers
                        pipe = None
                        await outq.put({"type": "done", "speakers": speakers})
                elif data["type"] == "stop":
                    pipe = None
            else:
                if pipe is None:
                    continue
                samples = np.frombuffer(msg["bytes"], dtype=np.float32)
                if samples.size == 0:
                    continue
                pipe.accept_waveform(samples)
                total_seconds += samples.size / SAMPLE_RATE
                # 推送本块产生的事件与流式 partial 预览
                for ev in pipe.events()[n_events:]:
                    n_events += 1
                    await outq.put({
                        "type": "event",
                        "start": round(ev.start, 3),
                        "end": round(ev.end, 3),
                        "speaker": ev.speaker_id,
                        "confidence": round(ev.confidence, 3),
                        "text": ev.text,
                    })
                partial = pipe.partial_text()
                if partial:
                    await outq.put({"type": "partial", "text": partial})
                await outq.put({"type": "progress", "t": round(total_seconds, 2)})
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()


def main():
    parser = argparse.ArgumentParser(description="sherpa-diarize Web 前端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--models-dir", default=str(ROOT / "models"), help="模型目录")
    args = parser.parse_args()

    global models_dir
    models_dir = Path(args.models_dir)
    if not (models_dir / "silero_vad.onnx").is_file():
        raise SystemExit(f"缺少 VAD 模型，请先运行 python3 scripts/download_models.py（--models-dir={models_dir}）")

    print(f"Web 前端: http://{args.host}:{args.port}")
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
