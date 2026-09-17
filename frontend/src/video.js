import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';
import classWorkerURL from '@ffmpeg/ffmpeg/worker?worker&url';
import { segmentRanges } from './video-utils.js';

const CORE_BASE = 'https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/esm';
let ffmpegPromise;

async function getFFmpeg() {
  if (!ffmpegPromise) {
    ffmpegPromise = (async () => {
      const ffmpeg = new FFmpeg();
      await ffmpeg.load({
        coreURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.wasm`, 'application/wasm'),
        classWorkerURL,
      });
      return ffmpeg;
    })();
  }
  return ffmpegPromise;
}

function readDuration(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const url = URL.createObjectURL(file);
    video.preload = 'metadata';
    video.onloadedmetadata = () => {
      const duration = video.duration;
      URL.revokeObjectURL(url);
      Number.isFinite(duration) && duration > 0
        ? resolve(duration)
        : reject(new Error('動画の長さを取得できませんでした。'));
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('この動画形式をブラウザで読み込めませんでした。'));
    };
    video.src = url;
  });
}

export async function splitVideoLocally(file, chunkSeconds = 60, onProgress = () => {}) {
  const ffmpeg = await getFFmpeg();
  const duration = await readDuration(file);
  const ranges = segmentRanges(duration, chunkSeconds);
  const extension = file.name.split('.').pop()?.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'mp4';
  const inputName = `input-${crypto.randomUUID()}.${extension}`;
  const segments = [];

  await ffmpeg.writeFile(inputName, await fetchFile(file));
  try {
    for (const range of ranges) {
      const outputName = `segment-${String(range.index + 1).padStart(3, '0')}.mp4`;
      const durationSeconds = range.end - range.start;
      const report = ({ progress }) => {
        const completed = range.index + Math.max(0, Math.min(1, progress || 0));
        onProgress(Math.round((completed / ranges.length) * 100));
      };
      ffmpeg.on('progress', report);
      try {
        let result = await ffmpeg.exec([
          '-ss', String(range.start), '-i', inputName, '-t', String(durationSeconds),
          '-map', '0:v:0?', '-map', '0:a:0?', '-c', 'copy', '-movflags', '+faststart', outputName,
        ]);
        if (result !== 0) {
          await ffmpeg.deleteFile(outputName).catch(() => {});
          result = await ffmpeg.exec([
            '-ss', String(range.start), '-i', inputName, '-t', String(durationSeconds),
            '-map', '0:v:0?', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '25', '-c:a', 'aac', '-movflags', '+faststart', outputName,
          ]);
        }
        if (result !== 0) throw new Error(`セグメント${range.index + 1}の作成に失敗しました。`);
        const data = await ffmpeg.readFile(outputName);
        const bytes = new Uint8Array(data);
        const blob = new Blob([bytes], { type: 'video/mp4' });
        segments.push({
          id: crypto.randomUUID(),
          ...range,
          bytes,
          url: URL.createObjectURL(blob),
          decision: 'pending',
          name: '',
        });
        await ffmpeg.deleteFile(outputName);
      } finally {
        ffmpeg.off('progress', report);
      }
      onProgress(Math.round(((range.index + 1) / ranges.length) * 100));
    }
  } finally {
    await ffmpeg.deleteFile(inputName).catch(() => {});
  }
  return segments;
}
