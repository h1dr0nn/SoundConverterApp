/**
 * Audio utility functions for file validation and metadata extraction
 */

const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.aiff', '.opus'];

/**
 * Check if a file is a valid audio file based on extension
 */
export const isAudioFile = (file) => {
  if (!file || !file.name) return false;
  const fileName = file.name.toLowerCase();
  return AUDIO_EXTENSIONS.some(ext => fileName.endsWith(ext));
};

/**
 * Format file size in bytes to human-readable string
 */
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/**
 * Format duration in seconds to MM:SS format
 */
export const formatDuration = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Extract file metadata for display
 */
export const getFileMetadata = async (file) => {
  const { size, name } = file;
  const path = file.path; // Tauri provides this on dropped files
  
  // Extract format from extension
  const parts = name.split('.');
  const format = parts.length > 1 ? parts.pop().toUpperCase() : 'UNKNOWN';
  
  return {
    id: crypto.randomUUID(),
    file,
    name,
    path: path || name, // Fallback if path not available
    format,
    size: formatFileSize(size),
    duration: '00:00', // Could use Web Audio API for real duration
    status: 'pending',
    error: null,
    output: null
  };
};

/**
 * Get file extension from filename
 */
export const getFileExtension = (filename) => {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
};

/**
 * Validate if output folder path is valid (non-empty)
 */
export const isValidOutputFolder = (path) => {
  return typeof path === 'string' && path.trim().length > 0;
};
