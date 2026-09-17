from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import json
import time
import uuid
from pathlib import Path

from db import get_db, create_tables
from models import Video, Segment
from video import split_video, create_zip_archive

app = FastAPI(title="SwipeCut API", version="1.0.0")

# CORS設定（本番環境用）
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://swipecut.kotalabo.com,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# データベーステーブル作成
create_tables()

# アプリケーション起動ログ
print("🚀 SwipeCut API starting...")
print(f"📁 Working directory: {os.getcwd()}")
print(f"🌐 Port: {os.getenv('PORT', '8000')}")
print(f"📂 Frontend dist exists: {os.path.exists('frontend/dist')}")
print("✅ Database tables created")
print("✅ Application ready!")

# 一時ストレージ設定（本格運用でも十分）
# 動画処理後はZIPファイルでダウンロードするため永続化不要
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/original")
SEGMENTS_DIR = os.getenv("SEGMENTS_DIR", "data/segments")
EXPORT_DIR = os.getenv("EXPORT_DIR", "data/export")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(95 * 1024 * 1024)))

# ディレクトリ作成
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEGMENTS_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

def cleanup_old_files():
    """古いファイルをクリーンアップ（24時間以上前）"""
    current_time = time.time()
    cutoff_time = current_time - (24 * 60 * 60)  # 24時間前
    
    for directory in [UPLOAD_DIR, SEGMENTS_DIR, EXPORT_DIR]:
        if os.path.exists(directory):
            for file_path in Path(directory).rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        print(f"🗑️ Cleaned up old file: {file_path}")
                    except Exception as e:
                        print(f"⚠️ Failed to clean up {file_path}: {e}")

# 起動時にクリーンアップ実行
cleanup_old_files()

# ヘルスチェック用のエンドポイント
@app.get("/health")
async def health_check():
    import os
    print(f"Health check called - Port: {os.getenv('PORT', '8000')}")
    return {
        "message": "SwipeCut API is running", 
        "status": "healthy",
        "port": os.getenv("PORT", "8000"),
        "frontend_exists": os.path.exists("frontend/dist"),
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

# 静的ファイル配信（フロントエンド用）
if os.path.exists("frontend/dist"):
    print("📂 Mounting static files from frontend/dist")
    
    # ルートパスでフロントエンドのindex.htmlを配信
    @app.get("/")
    async def serve_frontend():
        return FileResponse("frontend/dist/index.html")
    
    # 静的ファイルを /static パスで配信（APIルートより後にマウント）
    app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")
    
    print("✅ Static files mounted at /static")
    print("✅ Frontend served at /")
else:
    print("❌ Frontend dist directory not found")
    # フロントエンドがない場合のフォールバック
    @app.get("/")
    async def root():
        return {"message": "SwipeCut API is running", "status": "healthy", "frontend": "not found"}

@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    chunk_sec: int = Query(60, ge=5, le=600, description="分割秒数"),
    db: Session = Depends(get_db)
):
    """動画アップロード＆分割"""
    saved_path = None
    try:
        print(f"📤 Upload started: {file.filename}, chunk_sec: {chunk_sec}")
        print(f"📁 Upload directory: {UPLOAD_DIR}")
        print(f"📁 Segments directory: {SEGMENTS_DIR}")
        
        # ディレクトリの存在確認と作成
        if not os.path.exists(UPLOAD_DIR):
            print(f"📁 Creating upload directory: {UPLOAD_DIR}")
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        if not os.path.exists(SEGMENTS_DIR):
            print(f"📁 Creating segments directory: {SEGMENTS_DIR}")
            os.makedirs(SEGMENTS_DIR, exist_ok=True)
        
        if not file.content_type or not file.content_type.startswith("video/"):
            raise HTTPException(status_code=415, detail="動画ファイルを選択してください")

        original_name = Path(file.filename or "video.mp4").name
        extension = Path(original_name).suffix.lower()[:10] or ".mp4"
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{extension}")
        saved_path = file_path
        print(f"💾 Saving file to: {file_path}")
        
        # 書き込み権限の確認
        try:
            saved_bytes = 0
            with open(file_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    saved_bytes += len(chunk)
                    if saved_bytes > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="動画は500MB以下にしてください")
                    buffer.write(chunk)
            print(f"✅ File saved successfully, size: {saved_bytes} bytes")
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
            raise HTTPException(status_code=500, detail=f"Permission denied: {str(e)}")
        except Exception as e:
            print(f"❌ File save error: {e}")
            raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")
        
        # データベースに記録
        video = Video(filename=original_name, original_path=file_path)
        db.add(video)
        db.flush()
        print(f"💾 Video record created: ID {video.id}")
        
        # 動画分割
        print("🎬 Starting video segmentation...")
        segments_data = split_video(file_path, SEGMENTS_DIR, chunk_sec)
        print(f"✅ Video segmented into {len(segments_data)} segments")
        
        # セグメントをデータベースに記録
        for i, (start_sec, end_sec, segment_path) in enumerate(segments_data):
            segment = Segment(
                video_id=video.id,
                index=i,
                path=segment_path,
                start_sec=start_sec,
                end_sec=end_sec,
                decision="pending"
            )
            db.add(segment)
        
        db.commit()
        print("✅ All segments saved to database")
        
        return {"video_id": video.id, "segments_count": len(segments_data)}
    
    except HTTPException:
        db.rollback()
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)
        raise
    except Exception as e:
        db.rollback()
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)
        print(f"❌ Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/next_segment")
async def get_next_segment(
    video_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """次の未判定セグメントを取得"""
    segment = db.query(Segment).filter(
        Segment.video_id == video_id,
        Segment.decision == "pending"
    ).first()
    
    if not segment:
        return {"done": True}
    
    return {
        "done": False,
        "segment_id": segment.id,
        "index": segment.index,
        "path": segment.path,
        "start": segment.start_sec,
        "end": segment.end_sec,
        "name": segment.name,
        "url": f"/api/file/{segment.id}",
    }

@app.post("/api/decide")
async def decide_segment(
    segment_id: int = Query(...),
    decision: str = Query(..., pattern="^(keep|drop)$"),
    db: Session = Depends(get_db)
):
    """セグメント判定を保存"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    segment.decision = decision
    db.commit()
    
    return {"status": "success"}

@app.get("/api/progress")
async def get_progress(
    video_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """進捗状況を取得"""
    segments = db.query(Segment).filter(Segment.video_id == video_id).all()
    
    total = len(segments)
    kept = len([s for s in segments if s.decision == "keep"])
    dropped = len([s for s in segments if s.decision == "drop"])
    pending = len([s for s in segments if s.decision == "pending"])
    
    return {
        "total": total,
        "kept": kept,
        "dropped": dropped,
        "pending": pending
    }

@app.post("/api/name")
async def set_segment_name(
    segment_id: int = Query(...),
    name: str = Query(..., min_length=1, max_length=80),
    db: Session = Depends(get_db)
):
    """セグメントに名前を付与"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    segment.name = name.strip()
    db.commit()
    
    return {"status": "success"}

@app.get("/api/export")
async def export_kept_segments(
    video_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """KeepされたセグメントのメタデータをJSONで返す"""
    segments = db.query(Segment).filter(
        Segment.video_id == video_id,
        Segment.decision == "keep"
    ).all()
    
    manifest = {
        "video_id": video_id,
        "segments": [
            {
                "id": s.id,
                "index": s.index,
                "name": s.name or f"segment_{s.index:03d}",
                "start_sec": s.start_sec,
                "end_sec": s.end_sec,
            }
            for s in segments
        ]
    }
    
    # エクスポートディレクトリに保存
    export_path = os.path.join(EXPORT_DIR, f"video_{video_id}_manifest.json")
    with open(export_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest

@app.get("/api/export_zip")
async def export_zip(
    video_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """KeepされたセグメントをZIPで返す"""
    segments = db.query(Segment).filter(
        Segment.video_id == video_id,
        Segment.decision == "keep"
    ).all()
    
    if not segments:
        raise HTTPException(status_code=404, detail="No kept segments found")
    
    # ZIPファイル作成
    zip_path = os.path.join(EXPORT_DIR, f"video_{video_id}_kept_segments.zip")
    create_zip_archive(video_id, segments, zip_path)
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"video_{video_id}_kept_segments.zip"
    )

@app.get("/api/file/{segment_id}")
async def serve_file(segment_id: int, db: Session = Depends(get_db)):
    """登録済みセグメントだけを配信"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    segment_path = Path(segment.path).resolve()
    segment_root = Path(SEGMENTS_DIR).resolve()
    if segment_root not in segment_path.parents or not segment_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(segment_path, media_type="video/mp4")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
