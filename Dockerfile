# Railway用Dockerfile
FROM node:18-alpine AS frontend-builder

# フロントエンドをビルド
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# 本番用イメージ
FROM python:3.9-slim

# システムパッケージの更新とFFmpegのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# バックエンドの依存関係をインストール
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/ .

# フロントエンドのビルド結果をコピー
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 静的ファイルを配信するための設定
RUN pip install aiofiles

# ポート設定
EXPOSE 8000

# 起動コマンド
CMD ["sh", "-c", "echo 'Starting SwipeCut API...' && python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
