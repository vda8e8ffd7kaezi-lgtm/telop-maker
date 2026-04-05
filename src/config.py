"""TelopMaker 設定モジュール"""

from dataclasses import dataclass, field
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# デフォルトの出力先
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# faster-whisper設定
WHISPER_MODEL = "large-v3-turbo"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# 音声抽出設定
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1

# テロップ位置の選択肢
POSITION_PRESETS = {
    "下部中央": "Alignment=2",       # 下部中央（デフォルト）
    "上部中央": "Alignment=6",       # 上部中央
    "中央": "Alignment=5",           # 画面中央
}


@dataclass
class TelopStyle:
    """テロップのスタイル設定"""
    font_name: str = "Noto Sans CJK JP"
    font_size: int = 24
    primary_color: str = "&H00FFFFFF"   # 白（ASS形式: &HAABBGGRR）
    outline_color: str = "&H00000000"   # 黒
    outline_width: int = 2
    position: str = "下部中央"
    bold: bool = True
    background_box: bool = False

    def to_force_style(self) -> str:
        """FFmpegのforce_styleパラメータ用文字列を生成"""
        weight = 1 if self.bold else 0
        alignment = POSITION_PRESETS.get(self.position, "Alignment=2")
        parts = [
            f"FontName={self.font_name}",
            f"FontSize={self.font_size}",
            f"PrimaryColour={self.primary_color}",
            f"OutlineColour={self.outline_color}",
            f"Outline={self.outline_width}",
            f"Bold={weight}",
            alignment,
            "WrapStyle=2",
        ]
        if self.background_box:
            parts.append("BorderStyle=3")
        return ",".join(parts)
