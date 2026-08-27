"""OnlineClustering 单元测试：归入/新建/质心更新/合并/别名链。"""
import numpy as np
import pytest

from sherpa_diarize.clustering import OnlineClustering


def e(*xs):
    v = np.array(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


class TestAssign:
    def test_first_embedding_creates_speaker(self):
        c = OnlineClustering()
        sid, conf = c.assign(e(1, 0, 0))
        assert sid == 0
        assert conf == 0.0
        assert c.num_speakers == 1

    def test_similar_embedding_joins_same_speaker(self):
        c = OnlineClustering(threshold=0.8)
        sid0, _ = c.assign(e(1, 0, 0))
        v = e(0.95, 0.31, 0)  # 与 (1,0,0) 归一化后余弦 ≈ 0.951
        sid1, conf = c.assign(v)
        assert sid1 == sid0
        assert conf == pytest.approx(0.95 / np.sqrt(0.95**2 + 0.31**2), abs=1e-4)
        assert c.num_speakers == 1

    def test_dissimilar_embedding_creates_new_speaker(self):
        c = OnlineClustering(threshold=0.8)
        sid0, _ = c.assign(e(1, 0, 0))
        sid1, conf = c.assign(e(0, 1, 0))  # 正交
        assert sid1 != sid0
        assert conf == pytest.approx(0.0, abs=1e-6)  # 与最近质心相似度
        assert c.num_speakers == 2

    def test_centroid_updates_after_join(self):
        c = OnlineClustering(threshold=0.8, alpha=0.5)
        c.assign(e(1, 0, 0))
        c.assign(e(0.9, 0.44, 0))
        centroid = c._centroids[0]
        # EMA(0.5): 质心 x 分量从 1.0 向第二个向量方向下降，但仍在 0.95 与 1.0 之间
        assert 0.95 < centroid[0] < 1.0


class TestMerge:
    def test_similar_centroids_merge_with_alias(self):
        c = OnlineClustering(threshold=0.5, merge_threshold=0.9, merge_interval=1)
        # 两个高相似质心（同人不同片段），但 threshold=0.5 下不会被误并
        c.assign(e(1, 0, 0))
        # 强制第二个质心：喂一个与第一个低相似但自身稳定的向量
        c.assign(e(0, 1, 0))
        assert c.num_speakers == 2
        # 让质心 A 偏向 (1,0)，质心 B 偏向 (1,0) 附近 → 合并触发
        # 直接注入两个高相似质心，验证合并逻辑
        c._centroids = {0: e(1, 0, 0), 1: e(0.99, 0.14, 0)}
        c._counts = {0: 3, 1: 2}
        c._maybe_merge()
        assert c.num_speakers == 1
        assert c.resolve(1) == 0  # 别名链
        assert c.resolve(0) == 0

    def test_alias_chain_resolves(self):
        c = OnlineClustering()
        c._alias = {2: 1, 1: 0}
        assert c.resolve(2) == 0

    def test_distinct_centroids_not_merged(self):
        c = OnlineClustering(merge_threshold=0.9, merge_interval=1)
        c._centroids = {0: e(1, 0, 0), 1: e(0, 1, 0)}
        c._counts = {0: 1, 1: 1}
        c._maybe_merge()
        assert c.num_speakers == 2


class TestReset:
    def test_reset_clears_state(self):
        c = OnlineClustering()
        c.assign(e(1, 0, 0))
        c.reset()
        assert c.num_speakers == 0
        sid, _ = c.assign(e(1, 0, 0))
        assert sid == 0  # id 重新从 0 开始
