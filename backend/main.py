from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベーステーブル作成
create_tables()

@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    chunk_sec: int = Query(60, description="分割秒数"),
    db: Session = Depends(get_db)
):
    """動画アップロード＆分割"""
    try:
        # ファイル保存
        upload_dir = "data/original"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # データベースに記録
        video = Video(filename=file.filename, original_path=file_path)
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 動画分割
        segments_dir = "data/segments"
        segments_data = split_video(file_path, segments_dir, chunk_sec)
        
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

@app.get("/next_segment")
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

@app.post("/decide")
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

@app.get("/progress")
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

@app.post("/name")
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

@app.get("/export")
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
    export_dir = "data/export"
    os.makedirs(export_dir, exist_ok=True)
    
    export_path = os.path.join(export_dir, f"video_{video_id}_manifest.json")
    with open(export_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest

@app.get("/export_zip")
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
    export_dir = "data/export"
    os.makedirs(export_dir, exist_ok=True)
    
    zip_path = os.path.join(export_dir, f"video_{video_id}_kept_segments.zip")
    create_zip_archive(video_id, segments, zip_path)
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"video_{video_id}_kept_segments.zip"
    )

@app.get("/file")
async def serve_file(path: str = Query(...)):
    """ローカルファイル配信（開発用途限定）"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
