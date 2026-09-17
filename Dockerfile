FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY start.py ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV PORT=8000 \
    UPLOAD_DIR=/tmp/swipecut/original \
    SEGMENTS_DIR=/tmp/swipecut/segments \
    EXPORT_DIR=/tmp/swipecut/export \
    DATABASE_URL=sqlite:////tmp/swipecut/swipecut.db

EXPOSE 8000
CMD ["python", "start.py"]
