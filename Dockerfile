# ベースイメージを指定（Python 3.9の軽量版）
FROM python:3.9-slim-buster

# 作業ディレクトリを指定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt .
COPY bot.py .
COPY config.py .

# Pythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポートを指定（Cloud Runのデフォルトは8080）
EXPOSE 8080

# アプリケーションの起動コマンド
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8080"]
