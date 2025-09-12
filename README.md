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

- `POST /api/upload?chunk_sec=60` - 動画アップロード＆分割
- `GET /api/next_segment?video_id` - 次の未判定セグメント取得
- `POST /api/decide?segment_id=&decision=keep|drop` - 判定保存
- `GET /api/progress?video_id` - 進捗状況取得
- `POST /api/name?segment_id=&name=` - セグメント命名
- `GET /api/export?video_id` - KeepメタデータJSON出力
- `GET /api/export_zip?video_id` - KeepセグメントZIP出力
- `GET /api/file?path` - ローカルファイル配信

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
├── Dockerfile        # Railway用
├── railway.json      # Railway設定
├── .gitignore
└── README.md
```

## デプロイ（Railway - 推奨）

### 1. Railway CLIのインストール
```bash
npm install -g @railway/cli
```

### 2. ログイン
```bash
railway login
```

### 3. プロジェクト作成
```bash
railway init
```

### 4. デプロイ
```bash
railway up
```

### 5. 環境変数設定（オプション）
```bash
railway variables set UPLOAD_DIR=/tmp/swipecut/original
railway variables set SEGMENTS_DIR=/tmp/swipecut/segments
railway variables set EXPORT_DIR=/tmp/swipecut/export
```

### 6. カスタムドメイン設定
```bash
# カスタムドメインを追加
railway domain add swipecut.kotaro-design-lab.com
```

#### DNS設定（ドメインプロバイダー側）
```
Type: CNAME
Name: swipecut
Value: [Railwayが提供するドメイン]
TTL: 300
```

#### アクセスURL
- **本番環境**: `https://swipecut.kotaro-design-lab.com`
- **開発環境**: `http://localhost:5173`

## その他のデプロイ方法

### Render
- **無料枠**: 月750時間
- **FFmpeg対応**: ✅
- **制限**: 15分でスリープ

### Fly.io
- **無料枠**: 月2340時間
- **FFmpeg対応**: ✅
- **Docker**: 完全対応

### Google Cloud Run
- **無料枠**: 月200万リクエスト
- **FFmpeg対応**: ✅
- **スケーリング**: 自動

## ライセンス

MIT License