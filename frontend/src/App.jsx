import { useCallback, useEffect, useMemo, useState } from 'react';
import JSZip from 'jszip';
import { splitVideoLocally } from './video.js';
import { sanitizeFileName } from './video-utils.js';

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function App() {
  const [sourceName, setSourceName] = useState('');
  const [segments, setSegments] = useState([]);
  const [segmentName, setSegmentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const currentIndex = segments.findIndex((segment) => segment.decision === 'pending');
  const currentSegment = currentIndex >= 0 ? segments[currentIndex] : null;
  const progressData = useMemo(() => ({
    kept: segments.filter((segment) => segment.decision === 'keep').length,
    dropped: segments.filter((segment) => segment.decision === 'drop').length,
    pending: segments.filter((segment) => segment.decision === 'pending').length,
  }), [segments]);
  const isAllDone = segments.length > 0 && progressData.pending === 0;

  useEffect(() => {
    setSegmentName(currentSegment?.name || '');
  }, [currentSegment?.id, currentSegment?.name]);

  useEffect(() => {
    if (!loading) return undefined;
    const warnBeforeLeaving = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeLeaving);
    return () => window.removeEventListener('beforeunload', warnBeforeLeaving);
  }, [loading]);

  const handleDecision = useCallback((decision) => {
    if (!currentSegment || loading) return;
    setSegments((items) => items.map((segment) => (
      segment.id === currentSegment.id
        ? { ...segment, decision, name: decision === 'keep' ? segmentName.trim() : '' }
        : segment
    )));
    setSuccess(decision === 'keep' ? 'この場面を残しました。' : 'この場面を外しました。');
  }, [currentSegment, loading, segmentName]);

  useEffect(() => {
    const handleKey = (event) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === 'ArrowLeft') handleDecision('drop');
      if (event.key === 'ArrowRight') handleDecision('keep');
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [handleDecision]);

  const reset = () => {
    segments.forEach((segment) => URL.revokeObjectURL(segment.url));
    setSegments([]);
    setSourceName('');
    setError(null);
    setSuccess(null);
    setProcessingProgress(0);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!file.type.startsWith('video/')) {
      setError('動画ファイルを選択してください。');
      return;
    }
    if (file.size > 95 * 1024 * 1024) {
      setError('動画は95MB以下にしてください。');
      return;
    }

    reset();
    setLoading(true);
    setSourceName(file.name);
    try {
      const nextSegments = await splitVideoLocally(file, 60, setProcessingProgress);
      if (!nextSegments.length) throw new Error('分割できる場面がありませんでした。');
      setSegments(nextSegments);
      setSuccess(`${nextSegments.length}個の場面に分割しました。動画は端末の外へ送信されていません。`);
    } catch (reason) {
      setSourceName('');
      setError(reason instanceof Error ? reason.message : '動画の分割に失敗しました。');
    } finally {
      setLoading(false);
      setProcessingProgress(0);
    }
  };

  const handleExport = () => {
    const manifest = {
      source: sourceName,
      exported_at: new Date().toISOString(),
      kept_segments: segments.filter((segment) => segment.decision === 'keep').map((segment) => ({
        index: segment.index,
        name: segment.name || `segment_${String(segment.index + 1).padStart(3, '0')}`,
        start_sec: segment.start,
        end_sec: segment.end,
      })),
    };
    downloadBlob(new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' }), 'swipecut-manifest.json');
    setSuccess('選別結果をJSONで保存しました。');
  };

  const handleDownloadZip = async () => {
    const kept = segments.filter((segment) => segment.decision === 'keep');
    if (!kept.length) {
      setError('残す場面がありません。');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const zip = new JSZip();
      const usedNames = new Set();
      kept.forEach((segment) => {
        const base = sanitizeFileName(segment.name, `segment_${String(segment.index + 1).padStart(3, '0')}`);
        let name = `${base}.mp4`;
        let suffix = 2;
        while (usedNames.has(name)) name = `${base}_${suffix++}.mp4`;
        usedNames.add(name);
        zip.file(name, segment.bytes);
      });
      const blob = await zip.generateAsync({ type: 'blob', compression: 'STORE' });
      downloadBlob(blob, 'swipecut-kept-segments.zip');
      setSuccess('残した場面をZIPで保存しました。');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'ZIPの作成に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <header className="header">
        <div className="logo-container"><h1>SwipeCut</h1></div>
        <p>長い動画を1分ずつに分けて、残す場面だけを選ぶ。</p>
      </header>

      {error && <div className="error" role="alert">{error}</div>}
      {success && <div className="success" role="status">{success}</div>}

      {!sourceName ? (
        <section className="card">
          <label className="upload-area" htmlFor="fileInput">
            <span className="upload-text">動画ファイルを選択して分割</span>
            <span className="upload-button">ファイルを選ぶ</span>
            <input id="fileInput" type="file" accept="video/*" onChange={handleFileUpload} className="upload-input" />
          </label>
          <p className="upload-note">MP4など・95MBまで・動画はブラウザ内だけで処理します</p>
        </section>
      ) : currentSegment ? (
        <>
          <section className="card">
            <h2>場面 {currentSegment.index + 1} / {segments.length}</h2>
            <video className="video-player" controls src={currentSegment.url} key={currentSegment.id} />
            <input
              type="text"
              className="name-input"
              placeholder="残す場合のファイル名（任意）"
              value={segmentName}
              maxLength={80}
              onChange={(event) => setSegmentName(event.target.value)}
            />
            <div className="controls">
              <button className="control-button drop-button" onClick={() => handleDecision('drop')} disabled={loading}>← 外す</button>
              <button className="control-button keep-button" onClick={() => handleDecision('keep')} disabled={loading}>残す →</button>
            </div>
            <p className="keyboard-hint">キーボード: ← 外す / → 残す</p>
          </section>
          <Progress data={progressData} />
        </>
      ) : isAllDone ? (
        <>
          <section className="card complete-card">
            <h2>選別できました</h2>
            <p>{progressData.kept}個の場面を残します。</p>
            <div className="export-buttons">
              <button className="export-button" onClick={handleExport} disabled={loading}>結果をJSONで保存</button>
              <button className="export-button" onClick={handleDownloadZip} disabled={loading}>動画をZIPで保存</button>
              <button className="secondary-button" onClick={reset} disabled={loading}>別の動画を選ぶ</button>
            </div>
          </section>
          <Progress data={progressData} />
        </>
      ) : null}

      {loading && (
        <div className="loading" role="status">
          <div className="spinner" />
          <p>{processingProgress ? 'ブラウザ内で動画を分割中…' : 'ZIPを作成中…'}</p>
          {processingProgress > 0 && (
            <div className="progress-container">
              <div className="progress-bar"><div className="progress-fill" style={{ width: `${processingProgress}%` }} /></div>
              <p className="progress-text">{processingProgress}%</p>
              <p className="warning-text">処理が終わるまで、このタブを閉じないでください。</p>
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function Progress({ data }) {
  return (
    <section className="progress" aria-label="選別の進捗">
      <div className="progress-title">進捗</div>
      <div className="progress-stats">
        <div className="stat kept"><span className="stat-number">{data.kept}</span><span className="stat-label">残す</span></div>
        <div className="stat dropped"><span className="stat-number">{data.dropped}</span><span className="stat-label">外す</span></div>
        <div className="stat pending"><span className="stat-number">{data.pending}</span><span className="stat-label">未判定</span></div>
      </div>
    </section>
  );
}

export default App;
