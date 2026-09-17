import test from 'node:test';
import assert from 'node:assert/strict';
import { sanitizeFileName, segmentRanges } from '../src/video-utils.js';

test('segmentRanges keeps the final partial segment', () => {
  assert.deepEqual(segmentRanges(125, 60), [
    { index: 0, start: 0, end: 60 },
    { index: 1, start: 60, end: 120 },
    { index: 2, start: 120, end: 125 },
  ]);
});

test('segmentRanges supports videos shorter than one chunk', () => {
  assert.deepEqual(segmentRanges(6, 60), [{ index: 0, start: 0, end: 6 }]);
});

test('sanitizeFileName removes path and platform-reserved characters', () => {
  assert.equal(sanitizeFileName('../good:scene?.mp4'), 'good_scene_.mp4');
  assert.equal(sanitizeFileName('  '), 'segment');
});
