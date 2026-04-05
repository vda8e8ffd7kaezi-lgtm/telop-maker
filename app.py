"""TelopMaker - Streamlit アプリケーション"""

import tempfile
from pathlib import Path

import streamlit as st

from src.audio_extractor import extract_audio, get_video_info
from src.transcriber import transcribe, Segment
from src.srt_generator import generate_srt, save_srt
from src.video_composer import compose_video
from src.config import TelopStyle, POSITION_PRESETS, OUTPUT_DIR

st.set_page_config(page_title="TelopMaker", layout="wide")
st.title("TelopMaker")
st.caption("MP4動画から自動でテロップを生成")

# --- セッション状態の初期化 ---
if "segments" not in st.session_state:
    st.session_state.segments = None
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "processing" not in st.session_state:
    st.session_state.processing = False


# ============================================================
# サイドバー: テロップスタイル設定
# ============================================================
with st.sidebar:
    st.header("テロップ設定")

    font_size = st.slider("フォントサイズ", 12, 60, 24)
    font_color = st.color_picker("文字色", "#FFFFFF")
    outline_color = st.color_picker("縁取り色", "#000000")
    outline_width = st.slider("縁取り太さ", 0, 5, 2)
    position = st.selectbox("表示位置", list(POSITION_PRESETS.keys()))
    bold = st.checkbox("太字", value=True)
    background_box = st.checkbox("背景ボックス", value=False)


def _hex_to_ass_color(hex_color: str) -> str:
    """#RRGGBBをASS形式の&H00BBGGRRに変換"""
    hex_color = hex_color.lstrip("#")
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b.upper()}{g.upper()}{r.upper()}"


def build_style() -> TelopStyle:
    """サイドバーの設定からTelopStyleを構築"""
    return TelopStyle(
        font_size=font_size,
        primary_color=_hex_to_ass_color(font_color),
        outline_color=_hex_to_ass_color(outline_color),
        outline_width=outline_width,
        position=position,
        bold=bold,
        background_box=background_box,
    )


# ============================================================
# メインエリア: ファイルアップロード
# ============================================================
uploaded_file = st.file_uploader(
    "MP4ファイルをアップロード",
    type=["mp4"],
    help="MP4形式の動画ファイルを選択してください",
)

if uploaded_file is not None:
    # アップロードされたファイルを一時保存
    tmp_video = Path(tempfile.mktemp(suffix=".mp4"))
    tmp_video.write_bytes(uploaded_file.read())
    st.session_state.video_path = str(tmp_video)

    # 動画情報を表示
    try:
        info = get_video_info(tmp_video)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("長さ", info["duration_str"])
        col2.metric("解像度", f"{info['width']}x{info['height']}")
        col3.metric("コーデック", info["codec"])
        col4.metric("ファイルサイズ", f"{info['file_size_mb']} MB")
    except Exception as e:
        st.warning(f"動画情報の取得に失敗: {e}")

    # --- 文字起こし実行ボタン ---
    if st.button("文字起こし開始", type="primary", use_container_width=True):
        progress = st.progress(0, text="処理を開始...")

        try:
            # ステップ1: 音声抽出
            progress.progress(10, text="音声を抽出中...")
            audio_path = extract_audio(tmp_video)

            # ステップ2: 音声認識
            progress.progress(30, text="音声認識中（初回はモデルDLのため時間がかかります）...")
            segments = transcribe(audio_path)

            # 一時WAVを削除
            Path(audio_path).unlink(missing_ok=True)

            if not segments:
                st.warning("音声が認識されませんでした。動画に音声が含まれているか確認してください。")
            else:
                st.session_state.segments = segments
                progress.progress(100, text="文字起こし完了")
                st.success(f"{len(segments)} セグメントを認識しました")

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")


# ============================================================
# 認識結果の編集エリア
# ============================================================
if st.session_state.segments is not None:
    st.divider()
    st.subheader("認識結果の確認・編集")
    st.caption("テキストを直接編集できます。不要な行は空欄にすると除外されます。")

    edited_segments: list[Segment] = []

    for seg in st.session_state.segments:
        col_time, col_text = st.columns([1, 4])
        with col_time:
            start_m, start_s = divmod(seg.start, 60)
            end_m, end_s = divmod(seg.end, 60)
            st.text(f"{int(start_m):02d}:{start_s:05.2f}\n  ～\n{int(end_m):02d}:{end_s:05.2f}")
        with col_text:
            new_text = st.text_input(
                f"seg_{seg.index}",
                value=seg.text,
                label_visibility="collapsed",
                key=f"edit_{seg.index}",
            )
            if new_text.strip():
                edited_segments.append(Segment(
                    index=seg.index,
                    start=seg.start,
                    end=seg.end,
                    text=new_text.strip(),
                ))

    # --- テロップ合成実行 ---
    st.divider()
    if st.button("テロップを合成してMP4を出力", type="primary", use_container_width=True):
        if not edited_segments:
            st.warning("テロップにするセグメントがありません。")
        else:
            progress2 = st.progress(0, text="テロップを合成中...")

            try:
                # SRT生成
                progress2.progress(20, text="SRTファイルを生成中...")
                # 連番を振り直す
                for i, seg in enumerate(edited_segments, start=1):
                    seg.index = i

                srt_path = OUTPUT_DIR / "output.srt"
                save_srt(edited_segments, srt_path)

                # テロップ合成
                progress2.progress(40, text="テロップを動画に焼き込み中...")
                style = build_style()
                output_video = OUTPUT_DIR / "output.mp4"
                compose_video(
                    st.session_state.video_path,
                    srt_path,
                    output_video,
                    style=style,
                )

                progress2.progress(100, text="完了")
                st.success("テロップ付き動画を生成しました")

                # ダウンロードボタン
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    with open(output_video, "rb") as f:
                        st.download_button(
                            "MP4をダウンロード",
                            data=f,
                            file_name="telop_output.mp4",
                            mime="video/mp4",
                            use_container_width=True,
                        )
                with col_dl2:
                    srt_content = srt_path.read_text(encoding="utf-8")
                    st.download_button(
                        "SRTをダウンロード",
                        data=srt_content,
                        file_name="telop_output.srt",
                        mime="text/plain",
                        use_container_width=True,
                    )

            except Exception as e:
                st.error(f"合成エラー: {e}")
