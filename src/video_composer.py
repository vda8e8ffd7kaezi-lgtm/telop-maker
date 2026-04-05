"""動画合成モジュール - テロップをMP4に焼き込む"""

import shlex
import shutil
import subprocess
import tempfile
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

    FFmpegのsubtitlesフィルタはパス中の特殊文字に敏感なため、
    SRTファイルを一時的に安全なパスにコピーして処理する。
    """
    video_path = Path(video_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)

    if style is None:
        style = TelopStyle()

    force_style = style.to_force_style()

    # SRTを安全な一時ファイルにコピー（パスに特殊文字を含めない）
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_srt = tmp_dir / "subs.srt"
    shutil.copy2(srt_path, tmp_srt)

    # subtitlesフィルタ: ファイル名とforce_styleをシングルクォートで囲む
    # FFmpegフィルタ内のエスケープ: ' → '\'' , : はパス内のみエスケープ
    srt_path_escaped = str(tmp_srt).replace("'", r"'\''").replace(":", r"\:")
    vf = f"subtitles='{srt_path_escaped}':force_style='{force_style}'"

    # シェル経由で実行（フィルタ文字列のクォートを正しく処理するため）
    cmd = (
        f"ffmpeg -y "
        f"-i {shlex.quote(str(video_path))} "
        f'-vf "{vf}" '
        f"-c:v libx264 -preset medium -crf 23 -c:a copy "
        f"{shlex.quote(str(output_path))}"
    )

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"テロップ合成に失敗しました:\n{result.stderr}")
    finally:
        tmp_srt.unlink(missing_ok=True)
        tmp_dir.rmdir()

    return output_path


def compose_preview(
    video_path: str | Path,
    srt_path: str | Path,
    output_path: str | Path,
    start_sec: float,
    duration: float = 5.0,
    style: TelopStyle | None = None,
) -> Path:
    """
    指定区間だけテロップ付きプレビュー動画を高速生成する。

    Args:
        video_path: 入力動画ファイルのパス
        srt_path: SRTファイルのパス
        output_path: 出力プレビュー動画のパス
        start_sec: 切り出し開始時刻（秒）
        duration: 切り出し秒数（デフォルト5秒）
        style: テロップスタイル設定
    """
    video_path = Path(video_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)

    if style is None:
        style = TelopStyle()

    force_style = style.to_force_style()

    tmp_dir = Path(tempfile.mkdtemp())
    tmp_srt = tmp_dir / "subs.srt"
    shutil.copy2(srt_path, tmp_srt)

    srt_path_escaped = str(tmp_srt).replace("'", r"'\''").replace(":", r"\:")
    vf = f"subtitles='{srt_path_escaped}':force_style='{force_style}'"

    # -ss を入力前に置くことで高速シーク、-t で短い区間だけ処理
    cmd = (
        f"ffmpeg -y "
        f"-ss {start_sec:.2f} "
        f"-i {shlex.quote(str(video_path))} "
        f"-t {duration:.2f} "
        f'-vf "{vf}" '
        f"-c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 64k "
        f"{shlex.quote(str(output_path))}"
    )

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"プレビュー生成に失敗しました:\n{result.stderr}")
    finally:
        tmp_srt.unlink(missing_ok=True)
        tmp_dir.rmdir()

    return output_path
