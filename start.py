#!/usr/bin/env python3
"""
SwipeCut API 起動スクリプト
環境変数からポートを取得してuvicornを起動
"""
import os
import subprocess
import sys

def main():
    # 環境変数からポートを取得（デフォルト: 8000）
    port = os.getenv('PORT', '8000')
    
    print(f"🚀 Starting SwipeCut API...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🌐 Port: {port}")
    print(f"📂 Frontend dist exists: {os.path.exists('frontend/dist')}")
    
    # uvicornを起動
    cmd = [
        'python3', '-m', 'uvicorn',
        'main:app',
        '--host', '0.0.0.0',
        '--port', port
    ]
    
    print(f"🔧 Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting uvicorn: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
