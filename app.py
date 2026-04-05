"""TelopMaker - Streamlit アプリケーション"""

import tempfile
from pathlib import Path

import streamlit as st

from src.audio_extractor import extract_audio, get_video_info
from src.transcriber import transcribe, Segment
from src.srt_generator import save_srt
from src.video_composer import compose_video
from src.config import TelopStyle, POSITION_PRESETS, OUTPUT_DIR
from src.preview import render_preview_frame

st.set_page_config(
    page_title="TelopMaker",
    layout="wide",
    menu_items={
        "Get help": None,
        "Report a Bug": None,
        "About": "## TelopMaker\nMP4動画から自動でテロップを生成するアプリです。",
    },
)

# 右カラムをスクロール追従させるCSS
st.markdown("""
<style>
    footer { visibility: hidden; }
    .stButton button { min-height: 48px; }
    /* 右カラムをstickyにする */
    div[data-testid="stColumn"]:last-child {
        position: sticky;
        top: 3rem;
        align-self: flex-start;
    }
    @media (max-width: 768px) {
        .stMainBlockContainer { padding: 1rem 0.5rem; }
        section[data-testid="stSidebar"] { width: 280px !important; }
        div[data-testid="stColumn"]:last-child {
            position: static;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("TelopMaker")
st.caption("MP4動画から自動でテロップを生成")

# --- セッション状態の初期化 ---
for key, default in [
    ("segments", None),
    ("video_path", None),
    ("next_seg_id", 1000),
    ("preview_seg_idx", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default


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
    hex_color = hex_color.lstrip("#")
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b.upper()}{g.upper()}{r.upper()}"


def build_style() -> TelopStyle:
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
# ファイルアップロード
# ============================================================
uploaded_file = st.file_uploader(
    "MP4ファイルをアップロード",
    type=["mp4"],
    help="MP4形式の動画ファイルを選択してください",
)

if uploaded_file is not None:
    tmp_video = Path(tempfile.mktemp(suffix=".mp4"))
    tmp_video.write_bytes(uploaded_file.read())
    st.session_state.video_path = str(tmp_video)

    try:
        info = get_video_info(tmp_video)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("長さ", info["duration_str"])
        c2.metric("解像度", f"{info['width']}x{info['height']}")
        c3.metric("コーデック", info["codec"])
        c4.metric("ファイルサイズ", f"{info['file_size_mb']} MB")
    except Exception as e:
        st.warning(f"動画情報の取得に失敗: {e}")

    if st.button("文字起こし開始", type="primary", use_container_width=True):
        progress = st.progress(0, text="処理を開始...")
        try:
            progress.progress(10, text="音声を抽出中...")
            audio_path = extract_audio(tmp_video)
            progress.progress(30, text="音声認識中（初回はモデルDLのため時間がかかります）...")
            segs = transcribe(audio_path)
            Path(audio_path).unlink(missing_ok=True)
            if not segs:
                st.warning("音声が認識されませんでした。")
            else:
                st.session_state.segments = segs
                st.session_state.preview_seg_idx = 0
                progress.progress(100, text="文字起こし完了")
                st.success(f"{len(segs)} セグメントを認識しました")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")


# ============================================================
# 編集 + ライブプレビュー（左右レイアウト、右sticky）
# ============================================================
if st.session_state.segments and st.session_state.video_path:
    st.divider()
    segments = st.session_state.segments
    video_path = st.session_state.video_path

    try:
        vinfo = get_video_info(video_path)
        v_w, v_h = vinfo["width"], vinfo["height"]
    except Exception:
        v_w, v_h = 1280, 720

    # 左=編集、右=プレビュー
    edit_col, preview_col = st.columns([3, 2])

    # === 左: 編集エリア ===
    with edit_col:
        st.subheader("認識結果の確認・編集")

        edited_segments: list[Segment] = []

        def _make_focus_cb(idx: int):
            def cb():
                st.session_state.preview_seg_idx = idx
            return cb

        for i, seg in enumerate(segments):
            focus_cb = _make_focus_cb(i)
            is_active = (i == st.session_state.preview_seg_idx)

            # 選択中セグメントの視覚的ハイライト
            if is_active:
                st.markdown(
                    f'<div style="border-left:3px solid #FF4B4B; padding-left:8px;">',
                    unsafe_allow_html=True,
                )

            col_s, col_e, col_d = st.columns([2, 2, 1])
            with col_s:
                new_start = st.number_input(
                    "開始（秒）", min_value=0.0,
                    value=round(seg.start, 2), step=0.1, format="%.2f",
                    key=f"start_{seg.index}", on_change=focus_cb,
                )
            with col_e:
                new_end = st.number_input(
                    "終了（秒）", min_value=0.0,
                    value=round(seg.end, 2), step=0.1, format="%.2f",
                    key=f"end_{seg.index}", on_change=focus_cb,
                )
            with col_d:
                st.markdown("<div style='height:29px'></div>", unsafe_allow_html=True)
                delete = st.checkbox("除外", key=f"del_{seg.index}", on_change=focus_cb)

            new_text = st.text_area(
                f"#{i+1}", value=seg.text, height=68,
                key=f"edit_{seg.index}",
                label_visibility="collapsed",
                on_change=focus_cb,
            )

            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

            if new_text.strip() and not delete:
                edited_segments.append(Segment(
                    index=seg.index, start=new_start, end=new_end,
                    text=new_text.strip(),
                ))
            st.markdown("---")

        # 行追加
        def _add_segment():
            last_end = segments[-1].end if segments else 0.0
            nid = st.session_state.next_seg_id
            st.session_state.next_seg_id += 1
            segments.append(Segment(index=nid, start=round(last_end, 2),
                                     end=round(last_end + 3.0, 2), text=""))
        st.button("+ 行を追加", on_click=_add_segment, use_container_width=True)

    # === 右: プレビュー（sticky） ===
    with preview_col:
        st.subheader("プレビュー")

        sel = st.session_state.preview_seg_idx
        if 0 <= sel < len(segments):
            cur = segments[sel]
            cur_text = st.session_state.get(f"edit_{cur.index}", cur.text)
            cur_start = float(st.session_state.get(f"start_{cur.index}", cur.start))

            try:
                style = build_style()
                preview_png = render_preview_frame(video_path, cur_start + 0.5, cur_text, style, display_width=280)
                st.image(preview_png)

                # セグメント情報
                cur_end = float(st.session_state.get(f"end_{cur.index}", cur.end))
                sm, ss = divmod(cur_start, 60)
                em, es = divmod(cur_end, 60)
                st.caption(
                    f"セグメント #{sel+1} / {len(segments)}　"
                    f"({int(sm):02d}:{ss:04.1f} ~ {int(em):02d}:{es:04.1f})"
                )
            except Exception as e:
                st.warning(f"プレビュー取得エラー: {e}")

        # 前後ナビゲーション
        nav1, nav2 = st.columns(2)
        with nav1:
            if st.button("< 前へ", use_container_width=True, disabled=(sel <= 0)):
                st.session_state.preview_seg_idx = max(0, sel - 1)
                st.rerun()
        with nav2:
            if st.button("次へ >", use_container_width=True, disabled=(sel >= len(segments) - 1)):
                st.session_state.preview_seg_idx = min(len(segments) - 1, sel + 1)
                st.rerun()

    # --- テロップ合成実行 ---
    st.divider()
    if st.button("テロップを合成してMP4を出力", type="primary", use_container_width=True):
        if not edited_segments:
            st.warning("テロップにするセグメントがありません。")
        else:
            progress2 = st.progress(0, text="テロップを合成中...")
            try:
                progress2.progress(20, text="SRTファイルを生成中...")
                for idx_num, s in enumerate(edited_segments, start=1):
                    s.index = idx_num
                srt_path = OUTPUT_DIR / "output.srt"
                save_srt(edited_segments, srt_path)

                progress2.progress(40, text="テロップを動画に焼き込み中...")
                style = build_style()
                output_video = OUTPUT_DIR / "output.mp4"
                compose_video(video_path, srt_path, output_video, style=style)

                progress2.progress(100, text="完了")
                st.success("テロップ付き動画を生成しました")

                dl1, dl2 = st.columns(2)
                with dl1:
                    with open(output_video, "rb") as f:
                        st.download_button(
                            "MP4をダウンロード", data=f,
                            file_name="telop_output.mp4", mime="video/mp4",
                            use_container_width=True,
                        )
                with dl2:
                    srt_text = srt_path.read_text(encoding="utf-8")
                    st.download_button(
                        "SRTをダウンロード", data=srt_text,
                        file_name="telop_output.srt", mime="text/plain",
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"合成エラー: {e}")
