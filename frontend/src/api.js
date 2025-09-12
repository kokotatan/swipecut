const API_BASE = '/api';

export const uploadVideo = async (file, chunkSec = 60) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/upload?chunk_sec=${chunkSec}`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('Upload failed');
  }
  
  return response.json();
};

export const nextSegment = async (videoId) => {
  const response = await fetch(`${API_BASE}/next_segment?video_id=${videoId}`);
  
  if (!response.ok) {
    throw new Error('Failed to get next segment');
  }
  
  return response.json();
};

export const decide = async (segmentId, decision) => {
  const response = await fetch(`${API_BASE}/decide?segment_id=${segmentId}&decision=${decision}`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error('Failed to decide');
  }
  
  return response.json();
};

export const setName = async (segmentId, name) => {
  const response = await fetch(`${API_BASE}/name?segment_id=${segmentId}&name=${encodeURIComponent(name)}`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error('Failed to set name');
  }
  
  return response.json();
};

export const progress = async (videoId) => {
  const response = await fetch(`${API_BASE}/progress?video_id=${videoId}`);
  
  if (!response.ok) {
    throw new Error('Failed to get progress');
  }
  
  return response.json();
};

export const exportKept = async (videoId) => {
  const response = await fetch(`${API_BASE}/export?video_id=${videoId}`);
  
  if (!response.ok) {
    throw new Error('Failed to export');
  }
  
  return response.json();
};

export const downloadZip = async (videoId) => {
  const response = await fetch(`${API_BASE}/export_zip?video_id=${videoId}`);
  
  if (!response.ok) {
    throw new Error('Failed to download zip');
  }
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `video_${videoId}_kept_segments.zip`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};
