# SwipeCut

長い動画を1分ごとに分割し、カードを送る感覚で「残す / 外す」を判断できるWebツールです。残した場面だけを名前付きZIPでまとめて保存できます。

本番URL: https://swipecut.kotalabo.com

## 特徴

- 動画の分割はWebAssembly版FFmpegでブラウザ内だけで実行
- 動画をサーバーへアップロードしないプライバシー重視の構成
- ボタンまたは左右キーで「残す / 外す」を選別
- 残す場面のファイル名を指定可能
- 選別結果のJSON出力
- 残した動画だけをまとめたZIP出力

初回のみFFmpegの実行ファイルを読み込みます。ブラウザのメモリ内で処理するため、動画は1本95MBまでです。タブを閉じると分割結果と判定内容は消えます。

## 技術構成

- React + Vite
- ffmpeg.wasm
- JSZip
- Cloudflare Workers Static Assets

## ローカル開発

```bash
npm install
npm install --prefix frontend
npm run dev
```

## テスト

```bash
npm test
```

分割範囲・安全なファイル名の単体テスト、ESLint、本番ビルドを実行します。

## Cloudflareへデプロイ

```bash
npm run deploy
```

`wrangler.jsonc` で `frontend/dist` をCloudflare Workers Static Assetsとして配信し、`swipecut.kotalabo.com` をCustom Domainに設定しています。

## ライセンス

MIT License
