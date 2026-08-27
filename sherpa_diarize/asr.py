"""ASR 转写封装（sherpa-onnx OfflineRecognizer，Paraformer 中文模型）。

对每个 VAD turn 整段识别，与说话人事件同步输出转写文本。
"""
from __future__ import annotations

import numpy as np
import sherpa_onnx

__all__ = ["Asr"]


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
