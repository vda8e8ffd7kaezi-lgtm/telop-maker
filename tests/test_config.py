"""設定モジュールのユニットテスト"""

from src.config import TelopStyle, POSITION_PRESETS


def test_default_style():
    style = TelopStyle()
    assert style.font_size == 24
    assert style.bold is True
    assert style.position == "下部中央"


def test_force_style_default():
    style = TelopStyle()
    result = style.to_force_style()
    assert "FontName=Noto Sans CJK JP" in result
    assert "FontSize=24" in result
    assert "Alignment=2" in result
    assert "Bold=1" in result


def test_force_style_custom():
    style = TelopStyle(
        font_size=36,
        position="上部中央",
        bold=False,
        background_box=True,
    )
    result = style.to_force_style()
    assert "FontSize=36" in result
    assert "Alignment=6" in result
    assert "Bold=0" in result
    assert "BorderStyle=3" in result


def test_position_presets():
    assert "下部中央" in POSITION_PRESETS
    assert "上部中央" in POSITION_PRESETS
    assert "中央" in POSITION_PRESETS
