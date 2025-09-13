"""
ストレージ設定
本格運用時のストレージ選択肢
"""
import os
from enum import Enum

class StorageType(Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    RAILWAY_VOLUME = "railway_volume"

# 環境変数でストレージタイプを選択
STORAGE_TYPE = os.getenv("STORAGE_TYPE", StorageType.LOCAL.value)

# ストレージ設定
STORAGE_CONFIG = {
    StorageType.LOCAL.value: {
        "upload_dir": "data/original",
        "segments_dir": "data/segments", 
        "export_dir": "data/export"
    },
    StorageType.S3.value: {
        "bucket": os.getenv("S3_BUCKET"),
        "region": os.getenv("S3_REGION", "us-east-1"),
        "access_key": os.getenv("S3_ACCESS_KEY"),
        "secret_key": os.getenv("S3_SECRET_KEY")
    },
    StorageType.GCS.value: {
        "bucket": os.getenv("GCS_BUCKET"),
        "credentials_path": os.getenv("GCS_CREDENTIALS_PATH")
    },
    StorageType.RAILWAY_VOLUME.value: {
        "upload_dir": "/app/data/original",
        "segments_dir": "/app/data/segments",
        "export_dir": "/app/data/export"
    }
}

def get_storage_config():
    """現在のストレージ設定を取得"""
    return STORAGE_CONFIG.get(STORAGE_TYPE, STORAGE_CONFIG[StorageType.LOCAL.value])
