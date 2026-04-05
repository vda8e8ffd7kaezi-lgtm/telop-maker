"""音声抽出モジュール - MP4から音声をWAVとして抽出"""

import subprocess
import tempfile
from pathlib import Path

from src.config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS


def extract_audio(video_path: str | Path, output_path: str | Path | None = None) -> Path:
    """
    MP4動画から音声を抽出し、16kHzモノラルWAVファイルとして保存する。

    Args:
        video_path: 入力動画ファイルのパス
        output_path: 出力WAVファイルのパス（Noneの場合は一時ファイル）

    Returns:
        出力WAVファイルのパス
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".wav"))
    else:
        output_path = Path(output_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                          # 映像を無効化
        "-ar", str(AUDIO_SAMPLE_RATE),  # サンプルレート16kHz
        "-ac", str(AUDIO_CHANNELS),     # モノラル
        "-f", "wav",                    # WAV形式
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音声抽出に失敗しました:\n{result.stderr}")

    return output_path


def get_video_info(video_path: str | Path) -> dict:
    """
    動画のメタ情報を取得する。

    Returns:
        dict: duration, width, height, codec, file_size_mb
    """
    video_path = Path(video_path)
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"動画情報の取得に失敗しました:\n{result.stderr}")

    import json
    data = json.loads(result.stdout)

    # 映像ストリームを探す
    video_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))

    info = {
        "duration": duration,
        "duration_str": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
        "width": int(video_stream.get("width", 0)) if video_stream else 0,
        "height": int(video_stream.get("height", 0)) if video_stream else 0,
        "codec": video_stream.get("codec_name", "unknown") if video_stream else "unknown",
        "file_size_mb": round(file_size / (1024 * 1024), 1),
    }
    return info


def extract_frame(video_path: str | Path, timestamp: float) -> bytes:
    """
    動画から指定時刻のフレームをJPEG画像として抽出する。

    Args:
        video_path: 動画ファイルのパス
        timestamp: 抽出する時刻（秒）

    Returns:
        JPEG画像のバイナリデータ
    """
    cmd = [
        "ffmpeg",
        "-ss", f"{timestamp:.2f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-f", "image2",
        "-c:v", "mjpeg",
        "-q:v", "2",
        "pipe:1",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError("フレーム抽出に失敗しました")
    return result.stdout
