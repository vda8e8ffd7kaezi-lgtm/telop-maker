"""SRTファイル生成モジュール"""

from pathlib import Path

from src.transcriber import Segment


def _format_timecode(seconds: float) -> str:
    """秒数をSRT形式のタイムコード（HH:MM:SS,mmm）に変換"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list[Segment]) -> str:
    """
    セグメントリストからSRT形式の文字列を生成する。

    Args:
        segments: Segmentのリスト

    Returns:
        SRT形式の文字列
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_tc = _format_timecode(seg.start)
        end_tc = _format_timecode(seg.end)
        lines.append(f"{i}")
        lines.append(f"{start_tc} --> {end_tc}")
        lines.append(seg.text)
        lines.append("")  # 空行で区切り

    return "\n".join(lines)


def save_srt(segments: list[Segment], output_path: str | Path) -> Path:
    """
    セグメントリストをSRTファイルとして保存する。

    Args:
        segments: Segmentのリスト
        output_path: 出力ファイルパス

    Returns:
        出力ファイルのパス
    """
    output_path = Path(output_path)
    srt_content = generate_srt(segments)
    output_path.write_text(srt_content, encoding="utf-8")
    return output_path
