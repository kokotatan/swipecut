export function segmentRanges(duration, chunkSeconds = 60) {
  if (!Number.isFinite(duration) || duration <= 0) return [];
  const count = Math.ceil(duration / chunkSeconds);
  return Array.from({ length: count }, (_, index) => ({
    index,
    start: index * chunkSeconds,
    end: Math.min((index + 1) * chunkSeconds, duration),
  }));
}

export function sanitizeFileName(value, fallback = 'segment') {
  const printable = Array.from(value.normalize('NFKC'), (character) => (
    character.charCodeAt(0) < 32 ? '_' : character
  )).join('');
  const cleaned = printable
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .replace(/^[ ._]+|[ ._]+$/g, '')
    .slice(0, 80);
  return cleaned || fallback;
}
