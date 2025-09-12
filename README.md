# SwipeCut

動画を自動分割し、Tinder風UIで「残す/捨てる」を高速判定。各クリップに名前を付けて保存し、KeepのみをZIPで一括ダウンロードできます。（自動連結は実装しません）

## 前提

- macOS（例）
- ffmpeg/ffprobe インストール済み： `brew install ffmpeg`

## 起動

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 使用方法

1. ブラウザで `http://localhost:5173` にアクセス
2. 動画ファイルをアップロード（1分ごとに自動分割）
3. セグメントをTinder風UIで確認
4. 左右キーまたはボタンでKeep/Drop判定
5. Keepする場合はセグメント名を入力
6. 全件判定後、JSONエクスポートまたはZIPダウンロード

## 機能

- **動画分割**: FFmpegを使用して1分ごとに自動分割
- **Tinder風UI**: 直感的なスワイプ操作
- **キーボード操作**: 左右矢印キーで判定
- **セグメント命名**: Keepするセグメントに名前を付与
- **進捗表示**: リアルタイムで判定状況を表示
- **エクスポート**: JSON形式でのメタデータ出力
- **ZIPダウンロード**: Keepしたセグメントのみを一括ダウンロード

## 技術スタック

- **バックエンド**: FastAPI + FFmpeg + SQLite
- **フロントエンド**: React + Vite
- **データベース**: SQLAlchemy + SQLite

## API仕様

### エンドポイント

- `POST /upload?chunk_sec=60` - 動画アップロード＆分割
- `GET /next_segment?video_id` - 次の未判定セグメント取得
- `POST /decide?segment_id=&decision=keep|drop` - 判定保存
- `GET /progress?video_id` - 進捗状況取得
- `POST /name?segment_id=&name=` - セグメント命名
- `GET /export?video_id` - KeepメタデータJSON出力
- `GET /export_zip?video_id` - KeepセグメントZIP出力
- `GET /file?path` - ローカルファイル配信

## プロジェクト構造

```
swipecut/
├── backend/          # FastAPI バックエンド
│   ├── main.py       # メインAPI
│   ├── db.py         # データベース設定
│   ├── models.py     # SQLAlchemyモデル
│   ├── video.py      # FFmpeg処理
│   ├── requirements.txt
│   └── data/         # 動画・セグメント保存先
├── frontend/         # React フロントエンド
│   ├── src/
│   │   ├── App.jsx   # メインコンポーネント
│   │   ├── api.js    # API関数
│   │   └── styles.css
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

## デプロイ（Vercel）

### 1. Vercel CLIのインストール
```bash
npm i -g vercel
```

### 2. デプロイ
```bash
# プロジェクトルートで実行
vercel

# 本番デプロイ
vercel --prod
```

### 3. 環境変数設定
Vercelダッシュボードで以下の環境変数を設定：
- `PYTHONPATH`: `/var/task/backend`
- `NODE_ENV`: `production`

### 4. 制限事項
- **ファイル保存**: 一時ディレクトリに保存（再起動で削除）
- **データベース**: SQLite（永続化されない）
- **FFmpeg**: Vercel Functionsでは利用不可

### 本格運用の場合
- **AWS**: EC2 + S3 + RDS
- **Google Cloud**: Cloud Run + Cloud Storage + Cloud SQL
- **Railway**: 簡単デプロイ、FFmpeg対応

## ライセンス

MIT License