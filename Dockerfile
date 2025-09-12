# Railway用Dockerfile
FROM python:3.9-slim

# システムパッケージの更新とFFmpegのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Node.jsをインストール
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# 作業ディレクトリの設定
WORKDIR /app

# フロントエンドをビルド
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm install
COPY frontend/ .
RUN npm run build

# バックエンドの依存関係をインストール
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/ .

# 静的ファイルを配信するための設定
RUN pip install aiofiles

# 起動スクリプトをコピー
COPY start.py .

# ポート設定
EXPOSE 8000

# 起動コマンド
CMD ["python3", "start.py"]
