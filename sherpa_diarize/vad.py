"""流式 VAD 封装：把任意长度的音频块流式切分成说话片段（turn）。

内部使用 sherpa-onnx 的 Silero VAD（VoiceActivityDetector），
对外暴露 `accept_waveform` 增量输入与 `drain` 增量输出。

可选回调（供流式 ASR 并行消费语音）：
- `on_speech(samples)`：检测到新的语音样本即回调（窗口粒度），turn 内持续累积；
- `on_turn_end()`：一个 turn 结束（语音→静音切换或 flush）时回调一次。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import sherpa_onnx

__all__ = ["Turn", "Vad"]

SpeechCallback = Callable[[np.ndarray], None]
TurnEndCallback = Callable[[], None]


@dataclass
class Turn:
    """一个语音片段（VAD 检测到的一段连续语音）。

    start/end 均为相对流起点的秒数。
    """

    start: float
    end: float
    samples: np.ndarray  # float32, 单声道, sample_rate Hz


class Vad:
    """Silero VAD 封装。sample_rate 固定为 16kHz（silero_vad.onnx 仅支持 16k）。"""

    def __init__(
        self,
        model: str,
        min_silence_duration: float = 0.25,
        min_speech_duration: float = 0.25,
        max_speech_duration: float = 20.0,
        threshold: float = 0.5,
        sample_rate: int = 16000,
        num_threads: int = 1,
    ) -> None:
        self.sample_rate = sample_rate
        cfg = sherpa_onnx.VadModelConfig()
        cfg.sample_rate = sample_rate
        cfg.num_threads = num_threads
        cfg.silero_vad.model = model
        cfg.silero_vad.min_silence_duration = min_silence_duration
        cfg.silero_vad.min_speech_duration = min_speech_duration
        cfg.silero_vad.max_speech_duration = max_speech_duration
        cfg.silero_vad.threshold = threshold
        if not cfg.validate():
            raise ValueError(f"无效的 VAD 配置: {cfg}")
        # 缓冲池足够容纳一次 flush 后的残留段
        self._vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=30)
        self._window = cfg.silero_vad.window_size  # 512 samples = 32ms
        self._remainder = np.zeros(0, dtype=np.float32)
        self._num_consumed = 0  # 已送入 VAD 的样本总数，用于计算 turn 起点
        self._on_speech: SpeechCallback | None = None
        self._on_turn_end: TurnEndCallback | None = None
        self._in_speech = False  # 上一窗口是否处于语音段
        self._fed = 0  # 已回调的当前 turn 语音样本数

    def set_callbacks(
        self,
        on_speech: SpeechCallback | None = None,
        on_turn_end: TurnEndCallback | None = None,
    ) -> None:
        """设置语音样本 / turn 结束回调（供流式 ASR 并行消费）。"""
        self._on_speech = on_speech
        self._on_turn_end = on_turn_end

    def _feed_window(self, w: np.ndarray) -> None:
        """喂一个窗口并同步触发回调（语音样本增量 / turn 结束）。"""
        self._vad.accept_waveform(w)
        if self._vad.is_speech_detected():
            if not self._in_speech:
                self._in_speech = True
                self._fed = 0  # 新 turn，重新计数
            seg = self._vad.current_segment
            samples_arr = seg.samples
            n = len(samples_arr)
            if n > self._fed:
                # current_segment 是内部引用，立即拷贝再回调
                new = np.array(samples_arr[self._fed :], dtype=np.float32)
                self._fed = n
                if self._on_speech is not None:
                    self._on_speech(new)
        elif self._in_speech:
            self._in_speech = False
            if self._on_turn_end is not None:
                self._on_turn_end()

    def accept_waveform(self, samples: np.ndarray) -> None:
        """喂入任意长度的 float32 音频块。"""
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 1:
            raise ValueError(f"期望一维波形，得到 shape={samples.shape}")
        if self._remainder.size == 0:
            buf = samples
        else:
            buf = np.concatenate([self._remainder, samples])
        n_whole = len(buf) // self._window * self._window
        if n_whole > 0:
            windowed = buf[:n_whole].reshape(-1, self._window)
            for w in windowed:
                self._feed_window(w)
            self._num_consumed += n_whole
        self._remainder = buf[n_whole:]

    def flush(self) -> None:
        """流结束调用：把未完成的语音段输出，之后 drain 可拿到全部 turn。"""
        if self._remainder.size:
            self._vad.accept_waveform(self._remainder)
            self._num_consumed += self._remainder.size
            self._remainder = np.zeros(0, dtype=np.float32)
        self._vad.flush()
        if self._in_speech:
            self._in_speech = False
            if self._on_turn_end is not None:
                self._on_turn_end()

    def drain(self) -> list[Turn]:
        """取出所有已完成的 turn（不阻塞）。"""
        turns: list[Turn] = []
        while not self._vad.empty():
            seg = self._vad.front
            # sherpa-onnx 的 SpeechSegment.start 单位是样本数
            start = seg.start / self.sample_rate
            samples = np.asarray(seg.samples, dtype=np.float32)
            turns.append(Turn(start=start, end=start + len(samples) / self.sample_rate, samples=samples))
            self._vad.pop()
        return turns

    def reset(self) -> None:
        """清空内部状态，重新开始（新音频流）。"""
        self._vad.reset()
        self._remainder = np.zeros(0, dtype=np.float32)
        self._num_consumed = 0
        self._in_speech = False
        self._fed = 0
