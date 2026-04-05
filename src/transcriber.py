"""音声認識モジュール - faster-whisperによる文字起こし"""

from dataclasses import dataclass
from pathlib import Path

from src.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


@dataclass
class Segment:
    """音声認識の1セグメント"""
    index: int
    start: float   # 開始時刻（秒）
    end: float     # 終了時刻（秒）
    text: str      # 認識テキスト


def transcribe(
    audio_path: str | Path,
    model_size: str = WHISPER_MODEL,
    language: str = "ja",
    device: str = WHISPER_DEVICE,
    compute_type: str = WHISPER_COMPUTE_TYPE,
) -> list[Segment]:
    """
    音声ファイルを文字起こしし、タイムスタンプ付きセグメントのリストを返す。

    Args:
        audio_path: 入力音声ファイルのパス
        model_size: Whisperモデルサイズ
        language: 認識言語
        device: 実行デバイス（cpu/cuda）
        compute_type: 計算精度（int8/float16等）

    Returns:
        Segmentのリスト
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    raw_segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,          # VADフィルタで無音区間のハルシネーション抑制
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    segments = []
    for i, seg in enumerate(raw_segments, start=1):
        text = seg.text.strip()
        if text:
            segments.append(Segment(
                index=i,
                start=seg.start,
                end=seg.end,
                text=text,
            ))

    return segments
