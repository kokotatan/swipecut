import os
import io
import requests
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from pathlib import Path

# Google Photos API設定
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
CLIENT_SECRETS_FILE = 'client_secrets.json'  # 環境変数から取得
REDIRECT_URI = 'http://localhost:8000/api/google-photos/callback'

class GooglePhotosClient:
    def __init__(self):
        self.service = None
        self.credentials = None
        
    def get_authorization_url(self) -> str:
        """Google Photos認証URLを生成"""
        try:
            # 環境変数からクライアント設定を取得
            client_config = {
                "web": {
                    "client_id": os.getenv("GOOGLE_PHOTOS_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_PHOTOS_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
        except Exception as e:
            raise Exception(f"Failed to generate authorization URL: {e}")
    
    def authenticate_with_code(self, authorization_code: str) -> bool:
        """認証コードで認証を完了"""
        try:
            client_config = {
                "web": {
                    "client_id": os.getenv("GOOGLE_PHOTOS_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_PHOTOS_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            
            flow.fetch_token(code=authorization_code)
            self.credentials = flow.credentials
            
            # 認証情報を保存（実際の実装では安全なストレージを使用）
            self._save_credentials()
            
            # Google Photos APIサービスを初期化
            self.service = build('photoslibrary', 'v1', credentials=self.credentials)
            
            return True
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def _save_credentials(self):
        """認証情報を保存（簡易実装）"""
        if self.credentials:
            creds_data = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            
            # 実際の実装では暗号化して保存
            with open('google_photos_credentials.json', 'w') as f:
                json.dump(creds_data, f)
    
    def _load_credentials(self) -> bool:
        """保存された認証情報を読み込み"""
        try:
            if os.path.exists('google_photos_credentials.json'):
                with open('google_photos_credentials.json', 'r') as f:
                    creds_data = json.load(f)
                
                self.credentials = Credentials.from_authorized_user_info(creds_data, SCOPES)
                
                # トークンの有効性を確認
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                
                self.service = build('photoslibrary', 'v1', credentials=self.credentials)
                return True
        except Exception as e:
            print(f"Failed to load credentials: {e}")
        
        return False
    
    def get_video_list(self, page_size: int = 25) -> List[Dict]:
        """動画ファイルのリストを取得"""
        try:
            if not self.service:
                if not self._load_credentials():
                    raise Exception("Not authenticated")
            
            # 動画のみをフィルタリング
            request_body = {
                'filters': {
                    'mediaTypeFilter': {
                        'mediaTypes': ['VIDEO']
                    }
                },
                'pageSize': page_size
            }
            
            response = self.service.mediaItems().search(body=request_body).execute()
            return response.get('mediaItems', [])
            
        except HttpError as e:
            raise Exception(f"Google Photos API error: {e}")
        except Exception as e:
            raise Exception(f"Failed to get video list: {e}")
    
    def download_video(self, media_item_id: str, filename: str, download_dir: str) -> str:
        """動画ファイルをダウンロード"""
        try:
            if not self.service:
                if not self._load_credentials():
                    raise Exception("Not authenticated")
            
            # メディアアイテムの詳細を取得
            media_item = self.service.mediaItems().get(mediaItemId=media_item_id).execute()
            
            # 動画のダウンロードURLを取得
            base_url = media_item['baseUrl']
            download_url = f"{base_url}=dv"  # 動画の場合は=dvパラメータを追加
            
            # ファイルをダウンロード
            response = requests.get(download_url)
            response.raise_for_status()
            
            # ファイルを保存
            os.makedirs(download_dir, exist_ok=True)
            file_path = os.path.join(download_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return file_path
            
        except HttpError as e:
            raise Exception(f"Google Photos API error: {e}")
        except Exception as e:
            raise Exception(f"Failed to download video: {e}")
    
    def get_video_metadata(self, media_item_id: str) -> Dict:
        """動画のメタデータを取得"""
        try:
            if not self.service:
                if not self._load_credentials():
                    raise Exception("Not authenticated")
            
            media_item = self.service.mediaItems().get(mediaItemId=media_item_id).execute()
            
            return {
                'id': media_item['id'],
                'filename': media_item.get('filename', 'unknown.mp4'),
                'mimeType': media_item.get('mimeType', 'video/mp4'),
                'creationTime': media_item.get('mediaMetadata', {}).get('creationTime', ''),
                'width': media_item.get('mediaMetadata', {}).get('width', 0),
                'height': media_item.get('mediaMetadata', {}).get('height', 0),
                'duration': media_item.get('mediaMetadata', {}).get('video', {}).get('fps', 0)
            }
            
        except HttpError as e:
            raise Exception(f"Google Photos API error: {e}")
        except Exception as e:
            raise Exception(f"Failed to get video metadata: {e}")

# シングルトンインスタンス
google_photos_client = GooglePhotosClient()
