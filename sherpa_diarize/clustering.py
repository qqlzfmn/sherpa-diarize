"""在线说话人聚类：质心跟踪 + 周期性相似质心合并。

对每个 turn 的归一化 embedding：
- 与现有各说话人质心算余弦相似度（归一化后即点积）；
- 最高相似度 >= threshold → 归入该说话人，EMA 更新质心；
- 否则 → 新建说话人。

周期性把相似度过高的质心合并（修复同人过分割），被合并的 id 通过
`resolve()` 链式映射到保留 id，历史事件读取时一并归一。
"""
from __future__ import annotations

import numpy as np

__all__ = ["OnlineClustering"]


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


class OnlineClustering:
    def __init__(
        self,
        threshold: float = 0.6,
        alpha: float = 0.6,
        merge_threshold: float = 0.9,
        merge_interval: int = 16,
    ) -> None:
        """Args:
          threshold: 归入已有说话人的最小余弦相似度；越小越倾向合并，越大越倾向新建。
          alpha: 质心 EMA 更新系数（0~1），越大新 embedding 权重越高。
          merge_threshold: 周期合并时，质心间相似度超过该值则合并。
          merge_interval: 每多少个 turn 触发一次质心合并。
        """
        self.threshold = threshold
        self.alpha = alpha
        self.merge_threshold = merge_threshold
        self.merge_interval = merge_interval

        self._centroids: dict[int, np.ndarray] = {}  # speaker_id -> 归一化质心
        self._counts: dict[int, int] = {}  # speaker_id -> 已归入的 turn 数
        self._alias: dict[int, int] = {}  # 被合并 id -> 保留 id（可链式）
        self._next_id = 0
        self._turns = 0

    def assign(self, embedding: np.ndarray) -> tuple[int, float]:
        """把一个 turn 的 embedding 归入某说话人，返回 (speaker_id, confidence)。"""
        emb = _normalize(np.asarray(embedding, dtype=np.float32))
        if not self._centroids:
            return self._new_speaker(emb)

        ids = list(self._centroids)
        scores = np.array([float(np.dot(emb, self._centroids[i])) for i in ids])
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score >= self.threshold:
            sid = ids[best_idx]
            self._centroids[sid] = _normalize(
                self._centroids[sid] * (1 - self.alpha) + emb * self.alpha
            )
            self._counts[sid] += 1
            self._turns += 1
            self._maybe_merge()
            return sid, best_score
        return self._new_speaker(emb)

    def _new_speaker(self, emb: np.ndarray) -> tuple[int, float]:
        # 新建时的 confidence：与已有最近质心的相似度（说明"像谁但未达标"）
        conf = 0.0
        if self._centroids:
            conf = max(float(np.dot(emb, c)) for c in self._centroids.values())
        sid = self._next_id
        self._next_id += 1
        self._centroids[sid] = emb
        self._counts[sid] = 1
        self._turns += 1
        self._maybe_merge()
        return sid, conf

    def _maybe_merge(self) -> None:
        if self._turns % self.merge_interval != 0:
            return
        ids = list(self._centroids)
        if len(ids) < 2:
            return

        # union-find：质心两两相似度 > merge_threshold 则并集，根取最小 id
        parent = {i: i for i in ids}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                # 根取更小的 id，保证 id 稳定不漂移
                parent[max(ra, rb)] = min(ra, rb)

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if float(np.dot(self._centroids[a], self._centroids[b])) > self.merge_threshold:
                    union(a, b)

        roots: dict[int, list[int]] = {}
        for i in ids:
            roots.setdefault(find(i), []).append(i)

        new_centroids: dict[int, np.ndarray] = {}
        new_counts: dict[int, int] = {}
        for root, members in roots.items():
            if len(members) == 1:
                m = members[0]
                new_centroids[m] = self._centroids[m]
                new_counts[m] = self._counts[m]
                continue
            total = sum(self._counts[m] for m in members)
            merged = sum(
                self._centroids[m] * self._counts[m] for m in members
            ) / total
            for m in members:
                if m != root:
                    self._alias[m] = root
            new_centroids[root] = _normalize(merged)
            new_counts[root] = total
        self._centroids = new_centroids
        self._counts = new_counts

    def resolve(self, speaker_id: int) -> int:
        """把（可能已被合并的）speaker_id 映射到当前有效 id。"""
        while speaker_id in self._alias:
            speaker_id = self._alias[speaker_id]
        return speaker_id

    @property
    def num_speakers(self) -> int:
        return len(self._centroids)

    def reset(self) -> None:
        self._centroids.clear()
        self._counts.clear()
        self._alias.clear()
        self._next_id = 0
        self._turns = 0
