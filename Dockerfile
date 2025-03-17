# ベースイメージとしてPythonを使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# 環境変数の設定
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# ポートを公開
EXPOSE 5000

# Flaskアプリケーションを起動（gunicornを使う）
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
