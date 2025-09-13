# SwipeCut

なが〜い動画を、1分間隔に分割し、スワイプしながら整理できるサービス。Tinder風UIで「残す/捨てる」を直感的に選別し、KeepのみをZIPで一括ダウンロードできます。

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

### 通常の動画アップロード
1. ブラウザで `http://localhost:5173` にアクセス
2. 動画ファイルをアップロード（1分ごとに自動分割）
3. セグメントをTinder風UIで確認
4. 左右キーまたはボタンでKeep/Drop判定
5. Keepする場合はセグメント名を入力
6. 全件判定後、JSONエクスポートまたはZIPダウンロード

### Google Photos連携
1. 「Google Photosに接続」ボタンをクリック
2. Googleアカウントで認証
3. 「動画一覧を表示」でGoogle Photosの動画を確認
4. 分割したい動画の「分割開始」ボタンをクリック
5. 通常の分割・判定フローに進む

## 機能

- **動画分割**: FFmpegを使用して1分ごとに自動分割
- **Google Photos連携**: Google Photosに保存された動画を直接分割
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

### Google Photos連携エンドポイント

- `GET /api/google-photos/auth-url` - Google Photos認証URL取得
- `GET /api/google-photos/callback?code=` - 認証コールバック
- `GET /api/google-photos/videos?page_size=25` - Google Photos動画一覧取得
- `POST /api/google-photos/download?media_item_id=&chunk_sec=60` - Google Photos動画ダウンロード＆分割

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

### 5. 環境変数設定
```bash
# 基本設定
railway variables set UPLOAD_DIR=/tmp/swipecut/original
railway variables set SEGMENTS_DIR=/tmp/swipecut/segments
railway variables set EXPORT_DIR=/tmp/swipecut/export

# Google Photos API設定（Google Photos連携を使用する場合）
railway variables set GOOGLE_PHOTOS_CLIENT_ID=your_google_photos_client_id
railway variables set GOOGLE_PHOTOS_CLIENT_SECRET=your_google_photos_client_secret
```

### Google Photos API設定方法

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Photos Library APIを有効化
3. OAuth 2.0クライアントIDを作成
4. 承認済みリダイレクトURIに `https://your-domain.com/api/google-photos/callback` を追加
5. クライアントIDとクライアントシークレットを環境変数に設定

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