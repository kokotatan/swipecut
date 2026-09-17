# SwipeCut

長い動画を指定秒数ごとに分割し、カードを送る感覚で Keep / Drop を判断できるWebツールです。残したセグメントだけを名前付きZIPでまとめてダウンロードできます。

本番URL: https://swipecut.kotalabo.com

## 主な機能

- FFmpegによる動画の自動分割（初期値60秒）
- Keep / Drop のボタン・スワイプ・左右キー操作
- Keepするセグメントの命名
- 判定状況の進捗表示
- KeepメタデータのJSON出力
- Keepした動画だけをまとめたZIP出力

Cloudflareのリクエスト上限に余白を持たせるため、動画は1本95MBまでです。

アップロードされた動画、分割後の動画、判定内容は一時データです。Cloudflare Containerの停止・再作成後には保持されません。

## 技術構成

- フロントエンド: React + Vite
- API: FastAPI + SQLAlchemy + SQLite
- 動画処理: FFmpeg
- 配信: Cloudflare Workers + Containers

ブラウザごとに発行するセッションIDをCloudflare Workerが専用Containerへ割り当てます。異なる利用者の動画や判定データは同じContainerを共有しません。

## ローカル開発

Node.js 22、Python 3.12、FFmpeg / ffprobe が必要です。

```bash
npm install
npm install --prefix frontend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。Viteは `/api` と `/health` を `http://localhost:8000` へ転送します。

## テスト

```bash
npm test
```

バックエンドのAPI・実動画分割テスト、Workerの型検査、フロントエンドのlintと本番ビルドを実行します。

## Cloudflareへデプロイ

Cloudflare Workers Paidプラン、Docker、Wranglerへのログインが必要です。

```bash
npm run deploy
```

`wrangler.jsonc` に、ContainerとDurable Objectの紐付け、Dockerイメージ、`swipecut.kotalabo.com` のCustom Domain、Observabilityを定義しています。

## API

- `POST /api/upload?chunk_sec=60` — 動画のアップロードと分割
- `GET /api/next_segment?video_id=` — 次の未判定セグメント
- `GET /api/file/{segment_id}` — 登録済みセグメントの動画配信
- `POST /api/decide?segment_id=&decision=keep|drop` — 判定保存
- `POST /api/name?segment_id=&name=` — セグメント命名
- `GET /api/progress?video_id=` — 判定進捗
- `GET /api/export?video_id=` — KeepメタデータのJSON出力
- `GET /api/export_zip?video_id=` — Keep動画のZIP出力

## 構成

```text
swipecut/
├── backend/          # FastAPI、SQLite、FFmpeg処理、APIテスト
├── frontend/         # React UI
├── worker/           # セッション単位でContainerへ接続するWorker
├── Dockerfile        # フロントエンドとAPIをまとめるContainer
├── wrangler.jsonc    # Cloudflare Workers / Containers設定
└── package.json
```

## ライセンス

MIT License
