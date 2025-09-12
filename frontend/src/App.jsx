import React, { useState, useEffect, useCallback } from 'react';
import {
  uploadVideo,
  nextSegment,
  decide,
  setName,
  progress,
  exportKept,
  downloadZip
} from './api';

function App() {
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentSegment, setCurrentSegment] = useState(null);
  const [progressData, setProgressData] = useState(null);
  const [segmentName, setSegmentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

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

    try {
      const result = await uploadVideo(file, 60);
      setCurrentVideo({ id: result.video_id, filename: file.name });
      setSuccess(`動画をアップロードしました。${result.segments_count}個のセグメントに分割されました。`);
      
      // 最初のセグメントを取得
      await loadNextSegment(result.video_id);
    } catch (err) {
      setError('アップロードに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
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

  const isAllDone = progressData && progressData.pending === 0;

  return (
    <div className="container">
      <div className="header">
        <h1>SwipeCut</h1>
        <p>動画を自動分割し、Tinder風UIで「残す/捨てる」を高速判定</p>
      </div>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {!currentVideo ? (
        <div className="card">
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

      {loading && <div className="loading">処理中...</div>}
    </div>
  );
}

export default App;
