"""ASR 转写封装。

- `Asr`: 离线识别（Paraformer），对每个 turn 整段识别。
- `StreamingAsr`: 流式识别（OnlineRecognizer, Zipformer CTC），
  音频块增量解码，turn 结束时即刻出最终文本（无整段重识别延迟）。
"""
from __future__ import annotations

import numpy as np
import sherpa_onnx

__all__ = ["Asr", "StreamingAsr"]


class Asr:
    """Paraformer 离线识别。输入 16kHz 单声道 float32，输出文本。"""

    def __init__(
        self,
        model: str,
        tokens: str,
        num_threads: int = 1,
        provider: str = "cpu",
        debug: bool = False,
    ) -> None:
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=model,
            tokens=tokens,
            num_threads=num_threads,
            provider=provider,
            debug=debug,
        )

    def recognize(self, samples: np.ndarray) -> str:
        """识别一段语音，返回转写文本（无标点，可后续接标点模型）。"""
        stream = self._recognizer.create_stream()
        stream.accept_waveform(
            sample_rate=16000, waveform=np.ascontiguousarray(samples)
        )
        self._recognizer.decode_stream(stream)
        return stream.result.text


class StreamingAsr:
    """流式识别（Zipformer CTC）。turn 进行中增量喂音频，turn 结束出最终文本。

    用法（由 pipeline 驱动）：
        asr.accept_waveform(块)   # 语音块增量输入，内部增量解码
        text = asr.end_turn()     # turn 结束，返回最终文本
    """

    def __init__(
        self,
        model: str,
        tokens: str,
        num_threads: int = 1,
        provider: str = "cpu",
        debug: bool = False,
    ) -> None:
        self._recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
            tokens=tokens,
            model=model,
            num_threads=num_threads,
            provider=provider,
            debug=debug,
            sample_rate=16000,
            feature_dim=80,
            enable_endpoint_detection=False,
        )
        self._stream = None
        self._has_audio = False

    def accept_waveform(self, samples: np.ndarray) -> None:
        """喂入一个语音块（16kHz float32），内部增量解码。"""
        if self._stream is None:
            self._stream = self._recognizer.create_stream()
            self._has_audio = False
        if len(samples) == 0:
            return
        self._stream.accept_waveform(
            sample_rate=16000, waveform=np.ascontiguousarray(samples)
        )
        self._has_audio = True
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

    def end_turn(self) -> str:
        """turn 结束：取最终文本并复位内部状态。无音频时返回空串。

        CTC 模型需要尾部静音 padding 才能输出最后一段内容（参考官方示例），
        padding 长度 0.66s。
        """
        if self._stream is None or not self._has_audio:
            self._stream = None
            return ""
        # 尾部 padding：让尾部 chunk 完整解码
        self._stream.accept_waveform(
            sample_rate=16000, waveform=np.zeros(int(0.66 * 16000), dtype=np.float32)
        )
        self._stream.input_finished()
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)
        text = self._recognizer.get_result(self._stream)
        self._stream = None
        return text
