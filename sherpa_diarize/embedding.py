"""说话人 embedding 提取封装（sherpa-onnx SpeakerEmbeddingExtractor）。

返回 L2 归一化后的定长向量：归一化后余弦相似度等价于点积。
"""
from __future__ import annotations

import numpy as np
import sherpa_onnx

__all__ = ["SpeakerEmbedder"]


class SpeakerEmbedder:
    def __init__(
        self,
        model: str,
        num_threads: int = 1,
        provider: str = "cpu",
        debug: bool = False,
    ) -> None:
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=model,
            num_threads=num_threads,
            provider=provider,
            debug=debug,
        )
        if not config.validate():
            raise ValueError(f"无效的 embedding 配置: {config}")
        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

    @property
    def dim(self) -> int:
        """embedding 维度。"""
        return self._extractor.dim

    def extract(self, samples: np.ndarray) -> np.ndarray:
        """对一段语音提取 L2 归一化 embedding（shape=(dim,)）。

        samples 为任意采样率的单声道 float32；底层会自动处理采样率。
        """
        stream = self._extractor.create_stream()
        stream.accept_waveform(sample_rate=16000, waveform=np.ascontiguousarray(samples))
        stream.input_finished()
        if not self._extractor.is_ready(stream):
            raise ValueError(f"语音过短，无法提取 embedding（{len(samples)} samples）")
        emb = np.asarray(self._extractor.compute(stream), dtype=np.float32)
        norm = float(np.linalg.norm(emb))
        if norm == 0:
            raise ValueError("提取到零向量 embedding")
        return emb / norm
