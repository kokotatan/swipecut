# SwipeCut

動画を自動分割し、Tinder風UIで"残す/捨てる"を選択できるWebアプリケーションです。

## 概要

SwipeCutは、長い動画を1分ごとに自動分割し、Tinder風のスワイプUIで直感的に動画セグメントを選別できるツールです。左右キーまたはボタンでKeep/Drop判定を行い、結果をJSON形式でエクスポートできます。

## 技術スタック

- **バックエンド**: FastAPI + FFmpeg（動画分割）
- **フロントエンド**: React + Vite（UI/スワイプ選別）
- **データベース**: SQLite（Video/Segment管理）
- **開発環境**: Python 3.8+, Node.js 16+

## 機能

- 動画アップロード
- 1分ごとの自動分割
- Tinder風スワイプUI
- キーボード操作対応（左右キー）
- Keep/Drop判定
- 結果のJSONエクスポート

## セットアップ

### 前提条件

- Python 3.8以上
- Node.js 16以上
- FFmpeg（動画処理用）

### インストール

1. リポジトリをクローン
```bash
git clone https://github.com/your-username/swipecut.git
cd swipecut
```

2. バックエンドのセットアップ
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. フロントエンドのセットアップ
```bash
cd ../frontend
npm install
```

## 起動方法

### Backend

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

バックエンドAPIは `http://localhost:8000` で起動します。

### Frontend

```bash
cd frontend
npm run dev
```

フロントエンドアプリは `http://localhost:5173` で起動します。

## 使用方法

1. ブラウザで `http://localhost:5173` にアクセス
2. 動画ファイルをアップロード
3. 自動分割されたセグメントをTinder風UIで確認
4. 左右キーまたはボタンでKeep/Drop判定
5. 結果をJSON形式でエクスポート

## API仕様

### エンドポイント

- `POST /upload` - 動画アップロード
- `GET /videos` - 動画一覧取得
- `GET /segments/{video_id}` - セグメント一覧取得
- `POST /segments/{segment_id}/judge` - セグメント判定
- `GET /export/{video_id}` - 結果エクスポート

## 開発

### プロジェクト構造

```
swipecut/
├── backend/          # FastAPI バックエンド
│   ├── app/
│   ├── requirements.txt
│   └── main.py
├── frontend/         # React フロントエンド
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

### コントリビューション

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 作者

- [Your Name](https://github.com/your-username)

## サポート

問題や質問がある場合は、[Issues](https://github.com/your-username/swipecut/issues) で報告してください。