import subprocess
import os
import json
import math
import re
from pathlib import Path
from typing import List, Tuple
from models import Segment

def get_video_duration(video_path: str) -> float:
    """ffprobeで動画の長さを取得"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        raise Exception(f"Failed to get video duration: {e}")

def split_video(video_path: str, output_dir: str, chunk_sec: int = 60) -> List[Tuple[float, float, str]]:
    """動画を指定秒数で分割"""
    duration = get_video_duration(video_path)
    segments = []
    
    # 出力ディレクトリを作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if duration <= 0:
        raise ValueError("Video has no playable duration")

    video_name = Path(video_path).stem
    
    for segment_index in range(math.ceil(duration / chunk_sec)):
        start_sec = segment_index * chunk_sec
        end_sec = min(start_sec + chunk_sec, duration)
        clip_duration = end_sec - start_sec
        
        # セグメントファイル名
        segment_filename = f"{video_name}_segment_{segment_index:03d}.mp4"
        segment_path = os.path.join(output_dir, segment_filename)
        
        # ffmpegで分割（-c copyを優先、失敗時はTODOコメント）
        cmd = [
            "ffmpeg",
            "-v", "error",
            "-ss", str(start_sec),
            "-i", video_path,
            "-t", str(clip_duration),
            "-map", "0:v:0?",
            "-map", "0:a:0?",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            segment_path,
            "-y"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if not os.path.exists(segment_path) or os.path.getsize(segment_path) == 0:
                raise subprocess.CalledProcessError(1, cmd)
            segments.append((start_sec, end_sec, segment_path))
        except subprocess.CalledProcessError:
            fallback_cmd = [
                "ffmpeg",
                "-v", "error",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(clip_duration),
                "-map", "0:v:0?",
                "-map", "0:a:0?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-movflags", "+faststart",
                segment_path,
                "-y",
            ]
            try:
                subprocess.run(fallback_cmd, check=True, capture_output=True)
                segments.append((start_sec, end_sec, segment_path))
            except subprocess.CalledProcessError as error:
                raise RuntimeError(f"Failed to create segment {segment_index}") from error
    
    return segments

def create_zip_archive(video_id: int, segments: List[Segment], output_path: str) -> str:
    """KeepされたセグメントをZIPで圧縮（ZIP_STORED）"""
    import zipfile
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
        used_names = set()
        for segment in segments:
            if segment.decision == "keep" and os.path.exists(segment.path):
                raw_name = segment.name or f"segment_{segment.index:03d}"
                safe_name = re.sub(r"[^\w\-. ]+", "_", raw_name, flags=re.UNICODE).strip(" ._")
                safe_name = safe_name[:80] or f"segment_{segment.index:03d}"
                arcname = f"{safe_name}.mp4"
                suffix = 2
                while arcname in used_names:
                    arcname = f"{safe_name}_{suffix}.mp4"
                    suffix += 1
                used_names.add(arcname)
                zipf.write(segment.path, arcname)
    
    return output_path
