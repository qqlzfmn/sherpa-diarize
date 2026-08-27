"""流式 diarization 管线：VAD → embedding → 在线聚类 → 事件流。

`accept_waveform` 喂入音频块，管线内部完成切分/提特征/聚类，
事件按 (start, end, speaker_id, confidence) 增量累积，可导出 RTTM。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from sherpa_diarize.asr import Asr
from sherpa_diarize.clustering import OnlineClustering
from sherpa_diarize.embedding import SpeakerEmbedder
from sherpa_diarize.vad import Turn, Vad

__all__ = ["DiarizationEvent", "Pipeline"]


@dataclass
class DiarizationEvent:
    """一个说话人 turn 事件。start/end 为相对流起点的秒数，text 为该段 ASR 转写（未启用 ASR 时为空）。"""

    start: float
    end: float
    speaker_id: int
    confidence: float
    text: str = ""

    def to_rttm(self, filename: str = "audio") -> str:
        """转 RTTM 行（SPEAKER 类型）。"""
        return (
            f"SPEAKER {filename} 1 {self.start:.3f} {self.end - self.start:.3f} "
            f"<NA> <NA> {self.speaker_id} <NA> {self.confidence:.3f}"
        )


_FRAME_SECONDS = 0.032  # 能量帧长（32ms，与 VAD 窗口一致）
_SILENCE_RMS = 0.015  # RMS 低于该值视为静音
_MIN_KEEP_SECONDS = 0.1  # trim 后最短保留长度


def _trim_silence(samples: np.ndarray, sample_rate: int):
    """剥掉 turn 首尾的静音帧，返回 (samples, 剥掉的头部样本数)；全静音返回 (None, 0)。"""
    n_frame = int(_FRAME_SECONDS * sample_rate)
    n_keep = int(_MIN_KEEP_SECONDS * sample_rate)
    n_frames = len(samples) // n_frame
    if n_frames == 0:
        return (None, 0) if len(samples) < n_keep else (samples, 0)
    frames = samples[: n_frames * n_frame].reshape(-1, n_frame)
    rms = np.sqrt((frames**2).mean(axis=1))
    speech = rms >= _SILENCE_RMS
    if not speech.any():
        return (None, 0)
    first, last = int(np.argmax(speech)), n_frames - 1 - int(np.argmax(speech[::-1]))
    head, tail = first * n_frame, (last + 1) * n_frame
    trimmed = samples[head:tail]
    if len(trimmed) < n_keep:
        return (None, 0)
    return trimmed, head


class Pipeline:
    """把 Vad / SpeakerEmbedder / OnlineClustering 串成流式管线。

    典型用法：
        pipe = Pipeline(Vad(...), SpeakerEmbedder(...), OnlineClustering(...))
        for chunk in audio_chunks:
            pipe.accept_waveform(chunk)
        pipe.finish()
        events = pipe.events()
    """

    def __init__(
        self,
        vad: Vad,
        embedder: SpeakerEmbedder,
        clustering: OnlineClustering,
        asr: Asr | None = None,
        max_turn_seconds: float = 6.0,
        change_threshold: float = 0.6,
    ) -> None:
        """Args:
          vad / embedder / clustering: 三个构件。
          asr: 可选。提供时对每个 turn 同步做 ASR 转写，写入事件 text 字段。
          max_turn_seconds: 超过该时长的 turn 内部做说话人变化检测（滑动窗口
            embedding 序列找相似度骤降点）后切分，避免两人快速交替时混合成一个 turn。
          change_threshold: 相邻窗口 embedding 余弦相似度低于该值视为说话人切换点。
        """
        self.vad = vad
        self.embedder = embedder
        self.clustering = clustering
        self.asr = asr
        self.max_turn_seconds = max_turn_seconds
        self.change_threshold = change_threshold
        self._events: list[DiarizationEvent] = []
        self._finished = False

    # 子分段固定参数
    _FRAME_SECONDS = 0.032  # 能量帧长（32ms，与 VAD 窗口一致）
    _SILENCE_RMS = 0.015  # RMS 低于该值视为静音
    _MIN_SILENCE_SECONDS = 0.1  # 静音段最短长度才作为候选分割点
    _CONFIRM_SECONDS = 1.0  # 候选点两侧语音长度（用于确认是否切换说话人）
    _MIN_SUB_SECONDS = 1.0  # 切出的子段最短长度

    def _split_long_turn(self, turn: Turn) -> list[Turn]:
        """长 turn 内检测说话人切换并切分。

        思路：短静音常伴随说话人切换。先按能量找静音段作为候选分割点，
        再用候选点两侧语音的 embedding 相似度确认——同说话人停顿（相似度高）
        不切，确认切换（相似度低于 change_threshold）才切。
        """
        sr = self.vad.sample_rate
        n_frame = int(self._FRAME_SECONDS * sr)
        n_confirm = int(self._CONFIRM_SECONDS * sr)
        n_min_sub = int(self._MIN_SUB_SECONDS * sr)
        samples = turn.samples
        base = turn.start

        n_frames = len(samples) // n_frame
        frames = samples[: n_frames * n_frame].reshape(-1, n_frame)
        silence = np.sqrt((frames**2).mean(axis=1)) < self._SILENCE_RMS

        # 静音段 -> 候选分割点（取静音段中点，单位：样本偏移）
        candidates: list[int] = []
        i = 0
        while i < n_frames:
            if silence[i]:
                j = i
                while j < n_frames and silence[j]:
                    j += 1
                if (j - i) * n_frame >= int(self._MIN_SILENCE_SECONDS * sr):
                    candidates.append(((i + j) // 2) * n_frame)
                i = j
            else:
                i += 1

        cuts: list[int] = []
        for c in candidates:
            if c < n_confirm or len(samples) - c < n_confirm:
                continue  # 两侧没有足够语音
            before = samples[c - n_confirm : c]
            after = samples[c : c + n_confirm]
            try:
                sim = float(np.dot(self.embedder.extract(before), self.embedder.extract(after)))
            except ValueError:
                continue
            if sim >= self.change_threshold:
                continue  # 同说话人停顿，不切
            if cuts and c - cuts[-1] < n_min_sub:
                continue
            if len(samples) - c < n_min_sub:
                continue
            cuts.append(c)

        if not cuts:
            return [turn]

        bounds = [0] + cuts + [len(samples)]
        out: list[Turn] = []
        for a, b in itertools.pairwise(bounds):
            out.append(
                Turn(
                    start=base + a / sr,
                    end=base + b / sr,
                    samples=samples[a:b],
                )
            )
        return out

    def accept_waveform(self, samples: np.ndarray) -> None:
        """喂入一个音频块（float32，单声道，16kHz）。"""
        if self._finished:
            raise RuntimeError("管线已 finish，不能再喂入音频")
        self.vad.accept_waveform(samples)
        self._process_turns(self.vad.drain())

    def finish(self) -> None:
        """音频流结束：flush VAD 并处理最后一段语音。"""
        self.vad.flush()
        self._process_turns(self.vad.drain())
        self._finished = True

    def _process_turns(self, turns) -> None:
        for turn in turns:
            samples, offset = _trim_silence(turn.samples, self.vad.sample_rate)
            if samples is None:
                continue  # 全静音
            start = turn.start + offset / self.vad.sample_rate
            if len(samples) / self.vad.sample_rate > self.max_turn_seconds:
                subturns = self._split_long_turn(
                    Turn(start=start, end=start + len(samples) / self.vad.sample_rate, samples=samples)
                )
            else:
                subturns = [Turn(start=start, end=start + len(samples) / self.vad.sample_rate, samples=samples)]
            for st in subturns:
                try:
                    emb = self.embedder.extract(st.samples)
                except ValueError:
                    # 语音过短无法提 embedding：丢弃（VAD 已按 min_speech_duration 过滤，极少发生）
                    continue
                sid, conf = self.clustering.assign(emb)
                text = self.asr.recognize(st.samples) if self.asr else ""
                self._events.append(
                    DiarizationEvent(
                        start=st.start,
                        end=st.end,
                        speaker_id=self.clustering.resolve(sid),
                        confidence=conf,
                        text=text,
                    )
                )

    def events(self) -> list[DiarizationEvent]:
        """全部事件（speaker_id 已按最新质心合并结果归一）。"""
        return [
            DiarizationEvent(
                start=e.start,
                end=e.end,
                speaker_id=self.clustering.resolve(e.speaker_id),
                confidence=e.confidence,
                text=e.text,
            )
            for e in self._events
        ]

    def to_rttm(self, filename: str = "audio") -> str:
        return "\n".join(e.to_rttm(filename) for e in self.events()) + "\n"
