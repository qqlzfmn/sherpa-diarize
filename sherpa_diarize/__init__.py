"""sherpa-diarize: 端侧实时流式说话人分离。

基于 sherpa-onnx 的 VAD（Silero）+ 说话人 embedding（WeSpeaker/3D-Speaker）
+ 在线质心聚类，按音频块增量产出 (start, end, speaker_id, confidence) 事件。
"""
from sherpa_diarize.asr import Asr, StreamingAsr
from sherpa_diarize.clustering import OnlineClustering
from sherpa_diarize.embedding import SpeakerEmbedder
from sherpa_diarize.pipeline import DiarizationEvent, Pipeline
from sherpa_diarize.vad import Turn, Vad

__all__ = [
    "Asr",
    "DiarizationEvent",
    "OnlineClustering",
    "Pipeline",
    "SpeakerEmbedder",
    "StreamingAsr",
    "Turn",
    "Vad",
]

__version__ = "0.1.0"
