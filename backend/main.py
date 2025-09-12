from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import zipfile
from pathlib import Path

from db import get_db, create_tables
from models import Video, Segment
from video import split_video, create_zip_archive

app = FastAPI(title="SwipeCut API", version="1.0.0")

# CORS設定（本番環境用）
ALLOWED_ORIGINS = [
    "https://swipecut.kotaro-design-lab.com",
    "http://localhost:5173",  # 開発環境用
    "http://localhost:3000",  # 開発環境用
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

# 環境に応じたディレクトリ設定
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/original")
SEGMENTS_DIR = os.getenv("SEGMENTS_DIR", "data/segments")
EXPORT_DIR = os.getenv("EXPORT_DIR", "data/export")

# ディレクトリ作成
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SEGMENTS_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

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

# ルートエンドポイント（静的ファイル配信の前に定義）
@app.get("/")
async def root():
    return {"message": "SwipeCut API is running", "status": "healthy"}

# 静的ファイル配信（フロントエンド用）
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    chunk_sec: int = Query(60, description="分割秒数"),
    db: Session = Depends(get_db)
):
    """動画アップロード＆分割"""
    try:
        # ファイル保存
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # データベースに記録
        video = Video(filename=file.filename, original_path=file_path)
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 動画分割
        segments_data = split_video(file_path, SEGMENTS_DIR, chunk_sec)
        
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
        
        return {"video_id": video.id, "segments_count": len(segments_data)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        "name": segment.name
    }

@app.post("/api/decide")
async def decide_segment(
    segment_id: int = Query(...),
    decision: str = Query(..., regex="^(keep|drop)$"),
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
    name: str = Query(...),
    db: Session = Depends(get_db)
):
    """セグメントに名前を付与"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    segment.name = name
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
                "path": s.path
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

@app.get("/api/file")
async def serve_file(path: str = Query(...)):
    """ローカルファイル配信"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)