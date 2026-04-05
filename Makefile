PYTHON = .venv/bin/python
PIP = .venv/bin/pip
STREAMLIT = .venv/bin/streamlit

.PHONY: setup run test clean

# 初回セットアップ（Python仮想環境 + 依存パッケージ + FFmpeg）
setup:
	@echo "=== TelopMaker セットアップ ==="
	@command -v ffmpeg >/dev/null 2>&1 || { echo "FFmpegをインストール中..."; brew install ffmpeg; }
	/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
	$(PIP) install -r requirements.txt
	@echo ""
	@echo "セットアップ完了。 make run でアプリを起動できます。"

# アプリ起動
run:
	$(STREAMLIT) run app.py --server.port 8501

# テスト実行
test:
	$(PIP) install pytest -q
	$(PYTHON) -m pytest tests/ -v

# クリーンアップ
clean:
	rm -rf .venv .pytest_cache __pycache__ src/__pycache__ tests/__pycache__
	rm -rf output/*.mp4 output/*.srt output/*.wav
