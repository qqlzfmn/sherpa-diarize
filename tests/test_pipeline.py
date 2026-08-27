"""Pipeline 的 trim 与长 turn 子分段单元测试（使用假 embedder，不依赖模型文件）。"""
import numpy as np
import pytest

from sherpa_diarize.pipeline import Pipeline, _trim_silence
from sherpa_diarize.vad import Turn

SR = 16000
F1, F2 = 440.0, 880.0  # 两个"说话人"的基频


class FakeEmbedder:
    """按段内主导频率返回正交 embedding：(1,0,0) 或 (0,1,0)。"""

    def extract(self, samples):
        t = np.arange(len(samples)) / SR
        p1 = np.abs(np.sum(samples * np.sin(2 * np.pi * F1 * t)))
        p2 = np.abs(np.sum(samples * np.sin(2 * np.pi * F2 * t)))
        v = np.array([1.0, 0.0, 0.0]) if p1 >= p2 else np.array([0.0, 1.0, 0.0])
        return v


class FakeClustering:
    """记录 assign 的调用，返回递增 id。"""

    def __init__(self):
        self.assignments = []

    def assign(self, emb):
        self.assignments.append(emb.copy())
        return len(self.assignments) - 1, 1.0

    def resolve(self, sid):
        return sid


def sine(freq, seconds, silence=0.0):
    n = int(seconds * SR)
    if silence:
        n += int(silence * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t)
    x[: int(silence * SR)] = 0
    return x.astype(np.float32)


class TestTrim:
    def test_strips_leading_and_trailing_silence(self):
        # 静音与语音长度均取 32ms 帧的整数倍，避免帧量化误差
        x = np.concatenate([np.zeros(2560, np.float32), sine(F1, 1.024), np.zeros(1024, np.float32)])
        trimmed, offset = _trim_silence(x, SR)
        assert offset == 2560
        assert len(trimmed) == int(1.024 * SR)  # 恰好 1.024s 语音

    def test_all_silence_returns_none(self):
        assert _trim_silence(np.zeros(SR, np.float32), SR) == (None, 0)

    def test_no_silence_keeps_all(self):
        x = sine(F1, 1.024)  # 16384 samples = 32 帧
        trimmed, offset = _trim_silence(x, SR)
        assert offset == 0
        assert len(trimmed) == len(x)


class FakeVad:
    sample_rate = SR

    def __init__(self, turns=None):
        self._turns = list(turns or [])

    def accept_waveform(self, samples):
        pass

    def flush(self):
        pass

    def drain(self):
        out, self._turns = self._turns, []
        return out


class TestSplitLongTurn:
    def make_pipeline(self, max_turn=6.0, change_threshold=0.6):
        clustering = FakeClustering()
        pipe = Pipeline(vad=None, embedder=FakeEmbedder(), clustering=clustering,
                        max_turn_seconds=max_turn, change_threshold=change_threshold)
        pipe.vad = FakeVad()  # 仅提供 sample_rate
        return pipe, clustering

    def test_splits_at_speaker_change(self):
        """两段不同说话人语音夹 0.2s 静音 → 应在静音处切开。"""
        pipe, _ = self.make_pipeline()
        x = np.concatenate([sine(F1, 5.0), np.zeros(int(0.2 * SR), np.float32), sine(F2, 5.0)])
        turn = Turn(start=10.0, end=10.0 + len(x) / SR, samples=x)
        subs = pipe._split_long_turn(turn)
        assert len(subs) == 2
        assert subs[0].samples[-1] == 0  # 切点落在静音段内
        assert subs[1].samples[0] == 0
        # 切点时间 ≈ 静音段中点（5.0 + 0.1）
        cut = subs[0].end
        assert cut == pytest.approx(15.1, abs=0.05)

    def test_no_split_for_same_speaker_pause(self):
        """同人语音中间 0.3s 停顿 → 两侧 embedding 相同 → 不切。"""
        pipe, _ = self.make_pipeline()
        x = np.concatenate([sine(F1, 4.0), np.zeros(int(0.3 * SR), np.float32), sine(F1, 4.0)])
        turn = Turn(start=0.0, end=len(x) / SR, samples=x)
        subs = pipe._split_long_turn(turn)
        assert len(subs) == 1

    def test_short_turn_not_split(self):
        pipe, _ = self.make_pipeline(max_turn=6.0)
        x = sine(F1, 3.0)
        turn = Turn(start=0.0, end=3.0, samples=x)
        subs = pipe._split_long_turn(turn)
        assert len(subs) == 1

    def test_pipeline_events_after_finish(self):
        """端到端（假 embedder）：两个说话人交替，事件含正确 speaker_id。"""
        clustering = FakeClustering()
        pipe = Pipeline(vad=None, embedder=FakeEmbedder(), clustering=clustering,
                        max_turn_seconds=6.0, change_threshold=0.6)

        # 两个短 turn（同人 A 和同人 B）——不触发子分段
        turns = [
            Turn(start=0.0, end=2.0, samples=sine(F1, 2.0)),
            Turn(start=3.0, end=5.0, samples=sine(F2, 2.0)),
        ]
        pipe.vad = FakeVad(turns)
        pipe.finish()
        events = pipe.events()
        assert [ev.speaker_id for ev in events] == [0, 1]
        assert events[0].start == pytest.approx(0.0)
        assert events[0].end == pytest.approx(2.0, abs=0.05)
        assert all(ev.text == "" for ev in events)  # 未启用 ASR

    def test_events_carry_asr_text(self):
        """启用 asr 时，事件 text 字段携带识别结果。"""
        clustering = FakeClustering()

        class FakeAsr:
            def recognize(self, samples):
                return "你好世界"

        pipe = Pipeline(vad=None, embedder=FakeEmbedder(), clustering=clustering,
                        asr=FakeAsr(), max_turn_seconds=6.0, change_threshold=0.6)
        pipe.vad = FakeVad([Turn(start=0.0, end=2.0, samples=sine(F1, 2.0))])
        pipe.finish()
        events = pipe.events()
        assert len(events) == 1
        assert events[0].text == "你好世界"
