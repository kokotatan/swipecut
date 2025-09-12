import subprocess
import os
import json
from pathlib import Path
from typing import List, Tuple
from models import Video, Segment

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
    
    video_name = Path(video_path).stem
    segment_index = 0
    
    for start_sec in range(0, int(duration), chunk_sec):
        end_sec = min(start_sec + chunk_sec, duration)
        
        # セグメントファイル名
        segment_filename = f"{video_name}_segment_{segment_index:03d}.mp4"
        segment_path = os.path.join(output_dir, segment_filename)
        
        # ffmpegで分割（-c copyを優先、失敗時はTODOコメント）
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-c", "copy",  # コピーコーデック（高速）
            "-avoid_negative_ts", "make_zero",
            segment_path,
            "-y"  # 上書き許可
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            segments.append((start_sec, end_sec, segment_path))
            segment_index += 1
        except subprocess.CalledProcessError:
            # TODO: -c copyで失敗した場合のフォールバック処理
            # エンコードが必要な場合の処理をここに実装
            print(f"Warning: Failed to create segment {segment_index} with -c copy")
            # フォールバック処理（エンコード版）は必要に応じて実装
            raise Exception(f"Failed to create segment {segment_index}")
    
    return segments

def create_zip_archive(video_id: int, segments: List[Segment], output_path: str) -> str:
    """KeepされたセグメントをZIPで圧縮（ZIP_STORED）"""
    import zipfile
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
        for segment in segments:
            if segment.decision == "keep" and os.path.exists(segment.path):
                # ZIP内のファイル名
                arcname = f"{segment.name or f'segment_{segment.index:03d}'}.mp4"
                zipf.write(segment.path, arcname)
    
    return output_path
