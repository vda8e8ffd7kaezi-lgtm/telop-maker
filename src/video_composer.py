"""動画合成モジュール - テロップをMP4に焼き込む"""

import subprocess
from pathlib import Path

from src.config import TelopStyle


def compose_video(
    video_path: str | Path,
    srt_path: str | Path,
    output_path: str | Path,
    style: TelopStyle | None = None,
) -> Path:
    """
    SRTファイルのテロップを動画に焼き込む（ハードサブ）。

    Args:
        video_path: 入力動画ファイルのパス
        srt_path: SRTファイルのパス
        output_path: 出力動画ファイルのパス
        style: テロップスタイル設定

    Returns:
        出力動画ファイルのパス
    """
    video_path = Path(video_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)

    if style is None:
        style = TelopStyle()

    force_style = style.to_force_style()

    # SRTパスのエスケープ（FFmpegフィルタ用: コロンとバックスラッシュをエスケープ）
    srt_escaped = str(srt_path).replace("\\", "\\\\").replace(":", "\\:")

    # subtitlesフィルタでテロップ焼き込み
    vf = f"subtitles='{srt_escaped}':force_style='{force_style}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"テロップ合成に失敗しました:\n{result.stderr}")

    return output_path
