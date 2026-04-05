"""テロッププレビュー生成モジュール - FFmpegで実際と同じレンダリング"""

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.config import TelopStyle


def render_preview_frame(
    video_path: str,
    timestamp: float,
    text: str,
    style: TelopStyle,
    display_width: int = 280,
    max_height: int = 400,
) -> bytes:
    """
    FFmpegのsubtitlesフィルタでテロップを描画したプレビューフレームを返す。

    実際の合成出力と同じlibassエンジンを使用するため、
    プレビューと最終出力のテロップサイズ・見た目が完全に一致する。

    Args:
        video_path: 動画ファイルのパス
        timestamp: フレーム抽出時刻（秒）
        text: テロップテキスト
        style: テロップスタイル設定
        display_width: プレビュー最大幅（px）
        max_height: プレビュー最大高さ（px）

    Returns:
        PNG画像のバイト列
    """
    scale_filter = f"scale={display_width}:{max_height}:force_original_aspect_ratio=decrease"

    if not text or not text.strip():
        # テキストなしの場合はフレームだけ返す
        cmd = (
            f"ffmpeg -y "
            f"-ss {timestamp:.2f} "
            f"-i {shlex.quote(str(video_path))} "
            f'-vf "{scale_filter}" '
            f"-vframes 1 -f image2 -c:v png pipe:1"
        )
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode != 0 or not result.stdout:
            raise RuntimeError("フレーム抽出エラー")
        return result.stdout

    # 一時SRTファイルを作成（全時間帯をカバー）
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_srt = tmp_dir / "preview.srt"
    tmp_srt.write_text(
        f"1\n00:00:00,000 --> 09:59:59,999\n{text.strip()}\n",
        encoding="utf-8",
    )

    force_style = style.to_force_style()
    srt_escaped = str(tmp_srt).replace("'", r"'\''").replace(":", r"\:")

    # subtitlesフィルタ（フル解像度で描画）→ scaleでプレビューサイズに縮小
    vf = f"subtitles='{srt_escaped}':force_style='{force_style}',{scale_filter}"

    cmd = (
        f"ffmpeg -y "
        f"-ss {timestamp:.2f} "
        f"-i {shlex.quote(str(video_path))} "
        f'-vf "{vf}" '
        f"-vframes 1 -f image2 -c:v png pipe:1"
    )

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode != 0 or not result.stdout:
            stderr = result.stderr.decode("utf-8", errors="replace")[:300] if result.stderr else ""
            raise RuntimeError(f"プレビュー生成エラー: {stderr}")
        return result.stdout
    finally:
        tmp_srt.unlink(missing_ok=True)
        tmp_dir.rmdir()
