# sherpa-diarize

On-Device Real-time Streaming Speaker Diarization based on [Sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).

On-device real-time streaming speaker diarization ("who spoke when"), built on sherpa-onnx — runs on pure CPU / edge devices.

[中文](README.md)

## Goals

- **Real-time streaming**: processes audio incrementally in chunks, producing speaker-change events with low latency — no need to wait for a full recording.
- **On-device**: built on sherpa-onnx (ONNX Runtime); no GPU or cloud services required.
- **Plug and play**: two modes — file playback simulation and live microphone input.

## Core Approach

sherpa-onnx provides VAD and speaker-embedding capabilities; this project builds a streaming pipeline on top of them:

1. **Streaming VAD** (Silero VAD) segments the audio stream into turns. Long utterances additionally undergo in-turn speaker-change detection (energy/silence candidates + embedding verification on both sides) to avoid merging two rapidly alternating speakers into one turn.
2. **Speaker embedding** (WeSpeaker / 3D-Speaker) extracts a fixed-length vector (L2-normalized) for each turn.
3. **Online clustering / speaker tracking**: maintains a centroid per speaker (EMA-updated); cosine similarity above a threshold assigns the turn to an existing speaker, otherwise a new speaker is created. Similar centroids are periodically merged to repair over-segmentation.
4. **ASR transcription** (optional, two modes):
   - `--asr-mode offline`: transcribes the whole turn after it ends (Paraformer offline model, sub-segments transcribed independently);
   - `--asr-mode streaming`: incremental recognition while the turn is in progress; text is emitted as soon as it ends (Zipformer CTC streaming model, latency ≈ 0; long turns are sub-segmented and text is attached to the first sub-segment).
5. Emits speaker-turn events `(start, end, speaker_id, confidence, text)`, exportable as RTTM.

## Quick Start

### 1. Install dependencies

```bash
uv sync                    # core dependencies (sherpa-onnx + numpy + soundfile)
uv sync --extra mic        # add this for microphone input
```

### 2. Download models

```bash
python3 scripts/download_models.py                # overseas networks
python3 scripts/download_models.py --mirror https://ghfast.top/   # accelerated mirror for China
```

By default, models are downloaded to `models/`:

| File | Purpose | Size |
| --- | --- | --- |
| `silero_vad.onnx` | Silero VAD v4 (16 kHz) | 629 KB |
| `wespeaker_zh_cnceleb_resnet34.onnx` | Speaker embedding (Chinese) | 26.5 MB |
| `sherpa-onnx-paraformer-zh-small-2024-03-09/` | Paraformer Chinese ASR (offline, optional) | ~80 MB |
| `sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13/` | Zipformer CTC Chinese ASR (streaming, optional) | ~69 MB |
| `0-four-speakers-zh.wav` | Demo audio (4-speaker Chinese conversation) | 1.8 MB |

Optional flags to download only part of the files: `--vad-only` / `--embed-only` / `--asr-only` (offline ASR) / `--asr-streaming-only` (streaming ASR) / `--audio-only`.

### 3. Run examples

File playback (simulates a real-time stream in 200 ms chunks):

```bash
python3 examples/diarize_file.py \
    --wav models/0-four-speakers-zh.wav \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx
```

With ASR transcription (optional):

```bash
# Non-streaming (default): transcribe the whole turn after it ends
python3 examples/diarize_file.py \
    --wav models/0-four-speakers-zh.wav \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
    --asr-model models/sherpa-onnx-paraformer-zh-small-2024-03-09/model.int8.onnx \
    --asr-tokens models/sherpa-onnx-paraformer-zh-small-2024-03-09/tokens.txt

# Streaming: incremental recognition while the turn is in progress
python3 examples/diarize_file.py \
    --wav models/0-four-speakers-zh.wav \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
    --asr-mode streaming \
    --asr-model models/sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13/ctc-epoch-20-avg-1-chunk-16-left-128.int8.onnx \
    --asr-tokens models/sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13/tokens.txt
```

Live microphone (requires `uv sync --extra mic`):

```bash
python3 examples/diarize_mic.py \
    --vad-model models/silero_vad.onnx \
    --embed-model models/wespeaker_zh_cnceleb_resnet34.onnx \
    --asr-mode streaming \
    --asr-model models/sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13/ctc-epoch-20-avg-1-chunk-16-left-128.int8.onnx \
    --asr-tokens models/sherpa-onnx-streaming-zipformer-ctc-multi-zh-hans-int8-2023-12-13/tokens.txt
```

Web frontend (a brand-new Vite + Vue3 + TS project under `webui/`):

```bash
# Development (vite dev, proxied to the backend on 8000)
uv run python3 examples/web/server.py --port 8000   # backend (terminal 1)
cd webui && npm install && npm run dev               # frontend (terminal 2, http://localhost:5173)

# Production (built and served same-origin by the backend)
cd webui && npm run build
uv run python3 examples/web/server.py --port 8000    # open http://localhost:8000
```

Features: three audio sources (sample / upload / browser microphone), a canvas speaker timeline (colored segments + ruler + cursor + hover details + auto-follow), a transcript panel (streaming gray partial preview → smooth final text), speaker statistics, playback-rate control, and responsive layout. Audio is decoded to 16 kHz Float32 in the browser and fed chunk-by-chunk into the backend pipeline over a binary WebSocket.

UI screenshot check (dev tool, requires playwright + chromium):

```bash
uv sync --dev
python3 -m playwright install chromium
LD_LIBRARY_PATH=~/pw-libs .venv/bin/python3 examples/web/screenshot_ui.py --state done --out /tmp/ui.png
# After the screenshot, inspect it with a vision model (requires modelRoles.vision in the omp config; restart the session to apply)
```

### 4. Example output

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

The demo audio has 4 real speakers, matching the output; segments correspond one-to-one with sherpa-onnx offline diarization (pyannote segmentation + threshold 0.7), with boundary error ≤ 0.3 s.

Export RTTM:

```bash
python3 examples/diarize_file.py ... --rttm out.rttm
```

### 5. Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `--threshold` | 0.6 | Speaker assignment threshold; higher values tend to create new speakers |
| `--merge-threshold` | 0.9 | Periodic centroid-merge threshold |
| `--max-turn` | 6.0 | Turns longer than this (seconds) get in-turn speaker-change detection |
| `--change-threshold` | 0.6 | Similarity threshold confirming a speaker switch inside a long turn |
| `--chunk-ms` | 200 | Feed chunk duration in milliseconds (file playback) |
| `--realtime` | off | Play back the file at real-time speed |
| `--asr-model` / `--asr-tokens` | empty | Enable ASR transcription (both must be provided together) |
| `--asr-mode` | offline | `offline`: whole-turn recognition; `streaming`: incremental recognition |

## Directory Structure

```
sherpa-diarize/
├── sherpa_diarize/          # Core package
│   ├── vad.py               # Streaming VAD wrapper (turn segmentation)
│   ├── embedding.py         # Speaker embedding wrapper
│   ├── clustering.py        # Online clustering (centroid tracking + periodic merge)
│   ├── asr.py               # ASR wrapper (Asr offline / StreamingAsr streaming, optional)
│   └── pipeline.py          # Streaming pipeline (in-turn speaker-change detection, silence trim, RTTM export)
├── scripts/
│   └── download_models.py   # Downloads VAD / embedding models and demo audio
├── examples/
│   ├── diarize_file.py      # File playback (real-time simulation)
│   ├── diarize_mic.py       # Live microphone
│   └── web/                 # Web backend (FastAPI + WS binary audio stream)
│       ├── server.py
│       └── screenshot_ui.py  # Headless-browser screenshot (UI check)
├── webui/                   # Web frontend (Vite + Vue3 + TS, "ShengFen" design)
│   ├── src/components/       # AppHeader / SourceBar / TransportBar / Timeline / Transcript / SidePanel / StatusChip
│   ├── src/composables/      # session (WS) / playback / mic (recording)
│   └── dist/                 # Build output (npm run build, git-ignored)
├── tests/                   # Unit tests (clustering logic, trim, long-turn splitting)
└── pyproject.toml           # uv project
```

## Testing

```bash
uv run pytest tests/ -q
```

## On-device (Android) Roadmap

This project is an on-device Python demo; the ultimate goal is to run natively on Android:

- sherpa-onnx ships official Android examples (VAD, real-time ASR) and prebuilt APKs, see
  <https://k2-fsa.github.io/sherpa/onnx/vad/silero-vad.html#android-examples>;
- migration path: `Vad`/`SpeakerEmbedder`/`Asr`/`StreamingAsr` map directly to sherpa-onnx's C API
  (`VoiceActivityDetector`, `SpeakerEmbeddingExtractor`, `OfflineRecognizer`, `OnlineRecognizer`);
  the clustering/trim/change-detection logic in the pipeline is pure numerical code and can be ported to C++/JNI;
- model files (`silero_vad.onnx` + `wespeaker_zh_cnceleb_resnet34.onnx`, plus optional ASR models) can be packaged directly into the APK assets.

## Dependencies

- sherpa-onnx (ONNX Runtime; `sherpa-onnx-bin` provides `libonnxruntime.so`)
- numpy
- soundfile (audio file reading)
- optional: sounddevice (microphone input, `uv sync --extra mic`)
- optional: fastapi + uvicorn (Web frontend, `uv sync --extra web`)
