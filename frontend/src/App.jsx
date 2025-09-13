import React, { useState, useEffect, useCallback } from 'react';
import {
  uploadVideo,
  nextSegment,
  decide,
  setName,
  progress,
  exportKept,
  downloadZip,
  getGooglePhotosAuthUrl,
  getGooglePhotosVideos,
  downloadGooglePhotosVideo
} from './api';

function App() {
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentSegment, setCurrentSegment] = useState(null);
  const [progressData, setProgressData] = useState(null);
  const [segmentName, setSegmentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState(null);
  const [googlePhotosVideos, setGooglePhotosVideos] = useState([]);
  const [showGooglePhotos, setShowGooglePhotos] = useState(false);
  const [isGooglePhotosAuthenticated, setIsGooglePhotosAuthenticated] = useState(false);

  // キーボードイベントハンドラー
  const handleKeyPress = useCallback((event) => {
    if (!currentSegment) return;
    
    if (event.key === 'ArrowLeft') {
      handleDecision('drop');
    } else if (event.key === 'ArrowRight') {
      handleDecision('keep');
    }
  }, [currentSegment]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
    setEstimatedTime(null);
    
    // ファイルサイズから処理時間を推定
    const fileSizeMB = file.size / (1024 * 1024);
    const estimatedSeconds = Math.max(10, Math.ceil(fileSizeMB * 2)); // 1MBあたり2秒程度
    setEstimatedTime(estimatedSeconds);
    
    // タブ切り替え防止のイベントリスナー
    const beforeUnloadHandler = (e) => {
      e.preventDefault();
      e.returnValue = 'アップロード中です。タブを切り替えずにお待ちください。';
      return 'アップロード中です。タブを切り替えずにお待ちください。';
    };
    window.addEventListener('beforeunload', beforeUnloadHandler);

    try {
      // 進捗シミュレーション
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 10;
        });
      }, 1000);
      
      const result = await uploadVideo(file, 60);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setCurrentVideo({ id: result.video_id, filename: file.name });
      setSuccess(`動画をアップロードしました。${result.segments_count}個のセグメントに分割されました。`);
      
      // 最初のセグメントを取得
      await loadNextSegment(result.video_id);
    } catch (err) {
      setError('アップロードに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
      setUploadProgress(0);
      setEstimatedTime(null);
      window.removeEventListener('beforeunload', beforeUnloadHandler);
    }
  };

  const loadNextSegment = async (videoId) => {
    try {
      const segment = await nextSegment(videoId);
      if (segment.done) {
        setCurrentSegment(null);
        setSuccess('すべてのセグメントの判定が完了しました！');
      } else {
        setCurrentSegment(segment);
        setSegmentName(segment.name || '');
      }
      await loadProgress(videoId);
    } catch (err) {
      setError('セグメントの読み込みに失敗しました: ' + err.message);
    }
  };

  const loadProgress = async (videoId) => {
    try {
      const progressInfo = await progress(videoId);
      setProgressData(progressInfo);
    } catch (err) {
      console.error('進捗の取得に失敗しました:', err);
    }
  };

  const handleDecision = async (decision) => {
    if (!currentSegment || !currentVideo) return;

    setLoading(true);
    setError(null);

    try {
      // 判定を保存
      await decide(currentSegment.segment_id, decision);
      
      // Keepの場合は名前も保存
      if (decision === 'keep' && segmentName.trim()) {
        await setName(currentSegment.segment_id, segmentName.trim());
      }
      
      setSuccess(`セグメントを${decision === 'keep' ? '残す' : '捨てる'}に設定しました。`);
      
      // 次のセグメントを取得
      await loadNextSegment(currentVideo.id);
    } catch (err) {
      setError('判定の保存に失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!currentVideo) return;

    setLoading(true);
    setError(null);

    try {
      const manifest = await exportKept(currentVideo.id);
      const dataStr = JSON.stringify(manifest, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `video_${currentVideo.id}_manifest.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      setSuccess('JSONファイルをエクスポートしました。');
    } catch (err) {
      setError('エクスポートに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadZip = async () => {
    if (!currentVideo) return;

    setLoading(true);
    setError(null);

    try {
      await downloadZip(currentVideo.id);
      setSuccess('ZIPファイルをダウンロードしました。');
    } catch (err) {
      setError('ZIPダウンロードに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Google Photos関連の関数
  const handleGooglePhotosAuth = async () => {
    try {
      const { auth_url } = await getGooglePhotosAuthUrl();
      window.open(auth_url, '_blank');
      setIsGooglePhotosAuthenticated(true);
    } catch (err) {
      setError('Google Photos認証に失敗しました: ' + err.message);
    }
  };

  const loadGooglePhotosVideos = async () => {
    try {
      const { videos } = await getGooglePhotosVideos();
      setGooglePhotosVideos(videos);
      setShowGooglePhotos(true);
    } catch (err) {
      setError('Google Photos動画の取得に失敗しました: ' + err.message);
    }
  };

  const handleGooglePhotosVideoDownload = async (mediaItemId, filename) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
    setEstimatedTime(null);

    try {
      const result = await downloadGooglePhotosVideo(mediaItemId, 60);
      
      setCurrentVideo({ id: result.video_id, filename: result.filename });
      setSuccess(`Google Photosから動画をダウンロードしました。${result.segments_count}個のセグメントに分割されました。`);
      
      // 最初のセグメントを取得
      await loadNextSegment(result.video_id);
      setShowGooglePhotos(false);
    } catch (err) {
      setError('Google Photos動画のダウンロードに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
      setUploadProgress(0);
      setEstimatedTime(null);
    }
  };

  const isAllDone = progressData && progressData.pending === 0;

  return (
    <div className="container">
      <div className="header">
        <div className="logo-container">
          <h1>SwipeCut</h1>
        </div>
        <p>なが〜い動画を、1分間隔に分割し、スワイプしながら整理できるサービス。</p>
      </div>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {!currentVideo ? (
        <div className="card">
          {!showGooglePhotos ? (
            <>
              <div className="upload-area" onClick={() => document.getElementById('fileInput').click()}>
                <div className="upload-text">
                  動画ファイルを選択してアップロード
                </div>
                <button className="upload-button">
                  ファイルを選択
                </button>
                <input
                  id="fileInput"
                  type="file"
                  accept="video/*"
                  onChange={handleFileUpload}
                  className="upload-input"
                />
              </div>
              
              <div className="divider">
                <span>または</span>
              </div>
              
              <div className="google-photos-section">
                <h3>Google Photosから動画を選択</h3>
                <p>Google Photosに保存されている動画を直接分割できます</p>
                <div className="google-photos-buttons">
                  <button 
                    className="google-photos-auth-button"
                    onClick={handleGooglePhotosAuth}
                  >
                    Google Photosに接続
                  </button>
                  {isGooglePhotosAuthenticated && (
                    <button 
                      className="google-photos-load-button"
                      onClick={loadGooglePhotosVideos}
                    >
                      動画一覧を表示
                    </button>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="google-photos-video-list">
              <div className="google-photos-header">
                <h3>Google Photos動画一覧</h3>
                <button 
                  className="back-button"
                  onClick={() => setShowGooglePhotos(false)}
                >
                  ← 戻る
                </button>
              </div>
              
              <div className="video-grid">
                {googlePhotosVideos.map((video) => (
                  <div key={video.id} className="video-item">
                    <div className="video-thumbnail">
                      <img 
                        src={video.baseUrl + '=w200-h200'} 
                        alt={video.filename}
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'block';
                        }}
                      />
                      <div className="video-placeholder" style={{display: 'none'}}>
                        📹
                      </div>
                    </div>
                    <div className="video-info">
                      <div className="video-filename">{video.filename}</div>
                      <div className="video-date">
                        {new Date(video.mediaMetadata.creationTime).toLocaleDateString('ja-JP')}
                      </div>
                    </div>
                    <button 
                      className="download-button"
                      onClick={() => handleGooglePhotosVideoDownload(video.id, video.filename)}
                    >
                      分割開始
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
          {currentSegment && !isAllDone ? (
            <div className="card">
              <h2>セグメント {currentSegment.index + 1}</h2>
              <video
                className="video-player"
                controls
                src={`/api/file?path=${encodeURIComponent(currentSegment.path)}`}
                key={currentSegment.segment_id}
              />
              
              <input
                type="text"
                className="name-input"
                placeholder="セグメント名（Keepする場合のみ）"
                value={segmentName}
                onChange={(e) => setSegmentName(e.target.value)}
              />
              
              <div className="controls">
                <button
                  className="control-button drop-button"
                  onClick={() => handleDecision('drop')}
                  disabled={loading}
                >
                  ← 捨てる
                </button>
                <button
                  className="control-button keep-button"
                  onClick={() => handleDecision('keep')}
                  disabled={loading}
                >
                  残す →
                </button>
              </div>
              
              <div className="keyboard-hint">
                キーボード: ← 捨てる / → 残す
              </div>
            </div>
          ) : isAllDone ? (
            <div className="card">
              <h2>判定完了！</h2>
              <p>すべてのセグメントの判定が完了しました。</p>
              <div className="export-buttons">
                <button
                  className="export-button"
                  onClick={handleExport}
                  disabled={loading}
                >
                  JSONエクスポート
                </button>
                <button
                  className="export-button"
                  onClick={handleDownloadZip}
                  disabled={loading}
                >
                  ZIPダウンロード
                </button>
              </div>
            </div>
          ) : (
            <div className="loading">セグメントを読み込み中...</div>
          )}

          {progressData && (
            <div className="progress">
              <div className="progress-title">進捗状況</div>
              <div className="progress-stats">
                <div className="stat kept">
                  <span className="stat-number">{progressData.kept}</span>
                  <span className="stat-label">残す</span>
                </div>
                <div className="stat dropped">
                  <span className="stat-number">{progressData.dropped}</span>
                  <span className="stat-label">捨てる</span>
                </div>
                <div className="stat pending">
                  <span className="stat-number">{progressData.pending}</span>
                  <span className="stat-label">未判定</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>処理中...</p>
          {uploadProgress > 0 && (
            <div className="progress-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="progress-text">
                {Math.round(uploadProgress)}% 完了
                {estimatedTime && (
                  <span className="estimated-time">
                    （残り約{Math.max(0, Math.ceil(estimatedTime * (100 - uploadProgress) / 100))}秒）
                  </span>
                )}
              </p>
              <p className="warning-text">
                ⚠️ アップロード中です。タブを切り替えずにお待ちください。
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
