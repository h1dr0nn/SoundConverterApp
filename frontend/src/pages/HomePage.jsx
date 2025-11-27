import React, { useState, useEffect } from 'react';
import { FiSettings } from 'react-icons/fi';
import { listen } from '@tauri-apps/api/event';
import { dirname } from '@tauri-apps/api/path';
import { readBinaryFile } from '@tauri-apps/api/fs';
import { DragDropArea } from '../components/DragDropArea';
import { FileListPanel } from '../components/FileListPanel';
import { FormatSelector } from '../components/FormatSelector';
import { OutputFolderChooser } from '../components/OutputFolderChooser';
import { ProgressIndicator } from '../components/ProgressIndicator';
import { ToastMessage } from '../components/ToastMessage';
import { ModeSelector } from '../components/ModeSelector';
import { MasterControls } from '../components/MasterControls';
import { TrimControls } from '../components/TrimControls';
import { ErrorModal } from '../components/ErrorModal';
import { useTheme } from '../hooks/useTheme';
import { useConvertAudio } from '../hooks/useTauriCommand';
import { designTokens } from '../utils/theme';
import { themeClasses } from '../utils/themeColors';
import { getFileMetadata, formatFileSize, formatDuration, getAudioDuration } from '../utils/audioUtils';
import { notifySuccess, notifyError } from '../utils/notifications';
import { useSettingsContext } from '../context/SettingsContext';

const formatOptions = ['AAC', 'MP3', 'WAV', 'FLAC', 'OGG', 'M4A'];

export function HomePage({ 
  onOpenSettings, 
  files, 
  setFiles, 
  outputFolder, 
  setOutputFolder 
}) {
  const { theme } = useTheme();
  const { convert, loading: converting } = useConvertAudio();
  const { settings } = useSettingsContext();

  // Mode state
  const [mode, setMode] = useState('convert'); // 'convert' | 'master' | 'trim'

  // Convert mode - use default from settings
  const [selectedFormat, setSelectedFormat] = useState(settings.defaultFormat || 'AAC');

  // Master mode
  const [masterPreset, setMasterPreset] = useState('Music');
  const [masterParams, setMasterParams] = useState({
    target_lufs: -14.0,
    apply_compression: true,
    apply_limiter: true,
    output_gain: 0.0
  });

  // Trim mode
  const [trimThreshold, setTrimThreshold] = useState(-50.0);
  const [trimMinSilence, setTrimMinSilence] = useState(500);
  const [trimPadding, setTrimPadding] = useState(0);

  // Progress tracking
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState('');
  const [processingStatus, setProcessingStatus] = useState('Idle');

  // Error handling
  const [errorFiles, setErrorFiles] = useState([]);
  const [toast, setToast] = useState(null);

  // Sync default format from settings
  useEffect(() => {
    setSelectedFormat(settings.defaultFormat || 'AAC');
  }, [settings.defaultFormat]);

  // Handle files added from drag & drop or file picker
  const handleFilesAdded = async (newFiles) => {
    try {
      // Create minimal file objects immediately to show in UI
      const immediateFiles = newFiles.map(file => {
        const name = file.name || 'Unknown';
        const parts = name.split('.');
        let format = parts.length > 1 ? parts.pop().toUpperCase() : 'FILE';
        format = format.replace(/[^A-Z0-9]/g, '').substring(0, 4) || 'FILE';
        
        return {
          id: crypto.randomUUID(),
          file,
          name,
          path: file.path || name,
          format,
          size: formatFileSize(file.size || 0),
          sizeBytes: file.size || 0,
          duration: '--',
          status: 'loading',
          error: null,
          output: null
        };
      });

      // Filter out duplicates by comparing paths
      const existingPaths = new Set(files.map(f => f.path));
      const newUniqueFiles = immediateFiles.filter(file => !existingPaths.has(file.path));
      
      if (newUniqueFiles.length === 0) {
        const duplicateCount = immediateFiles.length;
        if (duplicateCount > 0) {
          setToast({ 
            type: 'info', 
            message: `${duplicateCount} duplicate file(s) skipped` 
          });
        }
        return;
      }

      const duplicateCount = immediateFiles.length - newUniqueFiles.length;
      if (duplicateCount > 0) {
        setToast({ 
          type: 'info', 
          message: `${duplicateCount} duplicate file(s) skipped` 
        });
      }

      // Add files to UI immediately
      setFiles(prev => [...prev, ...newUniqueFiles]);
      setToast({ type: 'info', message: `Adding ${newUniqueFiles.length} file(s)...` });

      // Auto-fill output folder if not already set
      if (!outputFolder && newUniqueFiles.length > 0) {
        if (settings.outputLocation === 'Same as source') {
          try {
            const firstFilePath = newUniqueFiles[0].path;
            
            // Check if path contains directory separators
            if (firstFilePath && (firstFilePath.includes('/') || firstFilePath.includes('\\'))) {
              const dir = await dirname(firstFilePath);
              setOutputFolder(dir);
            } else {
              // Drag files don't have full path, fallback to Downloads
              const { downloadDir } = await import('@tauri-apps/api/path');
              const downloads = await downloadDir();
              setOutputFolder(downloads);
            }
          } catch (error) {
            console.error('Failed to get directory:', error);
          }
        } else if (settings.outputLocation === 'Custom folder' && settings.customOutputFolder) {
          setOutputFolder(settings.customOutputFolder);
        } else {
          // Default to Downloads if no setting
          try {
            const { downloadDir } = await import('@tauri-apps/api/path');
            const downloads = await downloadDir();
            setOutputFolder(downloads);
          } catch (error) {
            console.error('Failed to get Downloads folder:', error);
          }
        }
      }

      // Load metadata for each file independently in background
      const maxSizeMB = parseInt(settings.maxFileSize);
      const maxSizeBytes = maxSizeMB * 1024 * 1024;

      newUniqueFiles.forEach(immediateFile => {
        // Each file gets its own async processing
        (async () => {
          try {
            // Check size limit first (already have size for drag, need to read for browse)
            let actualFile = immediateFile.file;
            let fileSize = immediateFile.sizeBytes;

            // If this is a path-based file from browse, read it now
            if (actualFile._needsReading) {
              try {
                const content = await readBinaryFile(actualFile.path);
                actualFile = new File([content], actualFile.name, {
                  type: 'audio/*',
                  lastModified: actualFile.lastModified
                });
                actualFile.path = immediateFile.path;
                fileSize = actualFile.size;

                // Update size in UI
                setFiles(prev => prev.map(f => 
                  f.id === immediateFile.id 
                    ? { ...f, size: formatFileSize(fileSize), sizeBytes: fileSize }
                    : f
                ));
              } catch (error) {
                console.error('Failed to read file:', immediateFile.path, error);
                setFiles(prev => prev.map(f => 
                  f.id === immediateFile.id 
                    ? { ...f, status: 'error', error: 'Failed to read file' }
                    : f
                ));
                return;
              }
            }

            // Check size limit
            if (fileSize > maxSizeBytes) {
              setFiles(prev => prev.map(f => 
                f.id === immediateFile.id 
                  ? { ...f, status: 'error', error: `Exceeds ${maxSizeMB}MB limit` }
                  : f
              ));
              return;
            }

            // Load duration in background
            let duration = '--';
            if (actualFile instanceof File && typeof actualFile.arrayBuffer === 'function') {
              try {
                const durationSeconds = await getAudioDuration(actualFile);
                duration = formatDuration(durationSeconds);
              } catch (error) {
                // Duration stays as '--' if fails
              }
            }

            // Update with duration and mark as ready
            setFiles(prev => prev.map(f => 
              f.id === immediateFile.id 
                ? { ...f, duration, status: 'ready' }
                : f
            ));
          } catch (error) {
            console.error('Failed to load metadata for', immediateFile.name, error);
            setFiles(prev => prev.map(f => 
              f.id === immediateFile.id 
                ? { ...f, status: 'error', error: 'Failed to load' }
                : f
            ));
          }
        })();
      });

    } catch (error) {
      console.error('Error adding files:', error);
      setToast({ type: 'error', message: 'Failed to add files' });
    }
  };

  // Handle clear all
  const handleClearAll = () => {
    setFiles([]);
    setOutputFolder('');
    setProgress(0);
    setCurrentFile('');
    setProcessingStatus('Idle');
    setErrorFiles([]);
  };

  // Handle remove individual file
  const handleRemoveFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  // Handle reload - reset all files to ready
  const handleReload = async () => {
    setFiles(prev => prev.map(f => ({
      ...f,
      status: f.status === 'error' || f.status === 'done' ? 'ready' : f.status,
      error: null,
      output: null
    })));
  };

  // Build payload for backend based on mode
  const buildPayload = () => {
    const filePaths = files.filter(f => f.status === 'ready').map(f => f.path);

    const basePayload = {
      files: filePaths,  // Required by Rust command
      output: outputFolder || './',
      concurrent_files: parseInt(settings.concurrentFiles) || 2,
    };

    if (mode === 'convert') {
      return {
        operation: 'convert',
        ...basePayload,
        format: selectedFormat.toLowerCase()
      };
    } else if (mode === 'master') {
      return {
        operation: 'master',
        ...basePayload,
        format: 'wav',  // Dummy value for Rust validation
        input_paths: filePaths,  // For Python backend
        output_directory: outputFolder || './',
        preset: masterPreset,
        parameters: masterParams
      };
    } else if (mode === 'trim') {
      return {
        operation: 'trim',
        ...basePayload,
        format: 'wav',  // Dummy value for Rust validation
        input_paths: filePaths,  // For Python backend
        output_directory: outputFolder || './',
        silence_threshold: trimThreshold,
        minimum_silence_ms: trimMinSilence,
        padding_ms: trimPadding
      };
    }
  };

  // Handle process button
  const handleProcess = async () => {
    if (files.length === 0) {
      setToast({ type: 'error', message: 'Please add files to process' });
      return;
    }

    if (!outputFolder) {
      setToast({ type: 'error', message: 'Please select an output folder' });
      return;
    }

    try {
      // Reset all files to ready (in case they were done/error from previous run)
      setFiles(prev => prev.map(f => ({ ...f, status: 'ready', error: null, output: null })));
      setProgress(0);
      setProcessingStatus('Starting...');
      setErrorFiles([]);

      const payload = buildPayload();
      
      if (settings.enableLogging) {
        console.log('[HomePage] Starting conversion with payload:', payload);
        console.log('[HomePage] Files:', files.length);
        console.log('[HomePage] Mode:', mode);
      }

      await convert(payload);

    } catch (error) {
      console.error('Processing error:', error);
      if (settings.enableLogging) {
        console.error('[HomePage] Full error details:', error);
      }
      
      // Mark all files as failed
      setFiles(prev => prev.map(f => ({
        ...f,
        status: 'error',
        error: 'Failed to start processing'
      })));
      
      setProgress(0);
      setProcessingStatus('Failed');
      
      // Show user-friendly error
      const isFFmpegMissing = error.message?.toLowerCase().includes('located') || 
                             error.message?.toLowerCase().includes('install ffmpeg');
      
      let userMessage = 'Processing failed. Please try again.';
      
      if (isFFmpegMissing) {
        userMessage = 'Audio processing tools not found. Please restart the app.';
      } else if (error.message?.includes('missing field')) {
        userMessage = 'Invalid configuration. Please check your settings.';
      } else if (error.message) {
        // Only show error message if it's not too technical
        const simplifiedMessage = error.message.replace(/`.*?`/g, '').trim();
        if (simplifiedMessage.length < 100 && !simplifiedMessage.includes('Error:')) {
          userMessage = simplifiedMessage;
        }
      }
      
      setToast({ type: 'error', message: userMessage });
    }
  };

  // Listen to conversion progress events
  useEffect(() => {
    let unlisten;

    const setupListener = async () => {
      unlisten = await listen('conversion-progress', (event) => {
        const payload = event.payload;

        // Handle progress events
        if (payload.event === 'progress') {
          const { index, total, file, status } = payload;
          
          setCurrentFile(file);
          setProgress((index / total) * 100);
          setProcessingStatus(`Processing ${index}/${total}`);

          // Update individual file status
          setFiles(prev => prev.map((f, i) => 
            i === index - 1 ? { ...f, status: status === 'processing' ? 'processing' : f.status } : f
          ));
        }

        // Handle complete event
        if (payload.event === 'complete') {
          const { status, message, outputs } = payload;

          if (status === 'success') {
            setProgress(100);
            setProcessingStatus('Complete');
            setCurrentFile('');
            
            // Mark all files as done
            setFiles(prev => prev.map((f, i) => ({
              ...f,
              status: 'done',
              output: outputs[i] || null
            })));

            setToast({ type: 'success', message: message || 'Processing complete!' });
            if (settings.notifications) {
              notifySuccess('Processing Complete', `${files.length} file(s) processed successfully`);
            }

            // Auto-clear if enabled
            if (settings.autoClear) {
              setTimeout(() => {
                handleClearAll();
              }, 2000); // Wait 2s for user to see completion
            }
          } else {
            // Error occurred - mark all files as failed
            setFiles(prev => prev.map(f => ({
              ...f,
              status: 'error',
              error: 'Processing failed'
            })));

            setProgress(0);
            setProcessingStatus('Failed');
            setCurrentFile('');
            
            // Show user-friendly error message
            const isFFmpegMissing = message?.toLowerCase().includes('located') || 
                                   message?.toLowerCase().includes('install ffmpeg');
            
            let userMessage = 'Processing failed. Check your files and try again.';
            
            if (isFFmpegMissing) {
              userMessage = 'Audio processing tools not found. Please restart the app.';
            } else if (message && message.length < 100 && !message.includes('Error:')) {
              userMessage = message;
            }
            
            setToast({ type: 'error', message: userMessage });
          }
        }
      });
    };

    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, [files]);

  // Calculate session summary
  const sessionSummary = {
    filesCount: files.length,
    format: mode === 'convert' ? selectedFormat : mode === 'master' ? `Master (${masterPreset})` : 'Trim',
    status: processingStatus
  };

  const hasReadyFiles = files.some(f => f.status === 'ready');
  const canProcess = hasReadyFiles && outputFolder && !converting;

  return (
    <div
      className={`min-h-screen bg-gradient-to-br ${themeClasses.pageBackground} px-4 py-10 text-slate-900 transition duration-smooth dark:text-slate-100`}
      style={{ fontFamily: designTokens.font }}
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        {/* Header */}
        <header className={`flex flex-col gap-4 rounded-card border ${themeClasses.card} p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">Sound Converter</p>
              <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Audio Processing Suite</h1>
              <p className="text-sm text-slate-600 dark:text-slate-300">Convert, master, and trim your audio files</p>
            </div>
            <button
              onClick={onOpenSettings}
              className={`flex h-12 w-12 items-center justify-center rounded-full border ${themeClasses.button} shadow-md transition duration-smooth hover:-translate-y-[1px] hover:shadow-lg`}
              aria-label="Settings"
            >
              <FiSettings className="h-6 w-6 text-slate-700 dark:text-slate-300" />
            </button>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[280px,1fr]">
          {/* Sidebar */}
          <aside className={`glass-surface relative overflow-hidden rounded-card border ${themeClasses.card} p-5 shadow-soft transition duration-smooth`}>
            <div className="absolute inset-0 bg-gradient-to-b from-white/70 via-white/30 to-white/0 opacity-80 dark:from-white/10 dark:via-white/5 dark:to-transparent" />
            <div className="relative space-y-6">
              {/* Mode Selector in Sidebar */}
              <ModeSelector selected={mode} onChange={setMode} />
              
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Workspace</p>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Session overview</h2>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {mode === 'convert' && 'Convert audio between different formats'}
                  {mode === 'master' && 'Enhance audio quality with professional presets'}
                  {mode === 'trim' && 'Automatically remove silence from recordings'}
                </p>
              </div>
              <div className={`space-y-3 rounded-2xl border ${themeClasses.surface} p-4`}>
                <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
                  <span>Files</span>
                  <span>{sessionSummary.filesCount}</span>
                </div>
                <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
                  <span>Mode</span>
                  <span>{sessionSummary.format}</span>
                </div>
                <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
                  <span>Status</span>
                  <span>{sessionSummary.status}</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="space-y-6">
            {/* Drag & Drop + Controls */}
            <section className={`grid gap-4 rounded-card border ${themeClasses.card} p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth lg:grid-cols-[1.5fr,1fr]`}>
              <DragDropArea onFilesAdded={handleFilesAdded} />
              <div className={`flex flex-col justify-between gap-6 rounded-card border ${themeClasses.surface} p-4`}>
                {mode === 'convert' && (
                  <FormatSelector formats={formatOptions} selected={selectedFormat} onSelect={setSelectedFormat} />
                )}
                {mode === 'master' && (
                  <MasterControls 
                    preset={masterPreset}
                    onPresetChange={setMasterPreset}
                    parameters={masterParams}
                    onParametersChange={setMasterParams}
                  />
                )}
                {mode === 'trim' && (
                  <TrimControls
                    threshold={trimThreshold}
                    onThresholdChange={setTrimThreshold}
                    minSilence={trimMinSilence}
                    onMinSilenceChange={setTrimMinSilence}
                    padding={trimPadding}
                    onPaddingChange={setTrimPadding}
                  />
                )}
                <OutputFolderChooser path={outputFolder} onChoose={setOutputFolder} />
              </div>
            </section>

            {/* File List + Progress */}
            <section className={`grid gap-4 rounded-card border ${themeClasses.card} p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth lg:grid-cols-[1.5fr,1fr]`}>
              <FileListPanel 
                files={files} 
                onClearAll={handleClearAll} 
                onRemoveFile={handleRemoveFile}
                onReload={handleReload}
              />
              <div className="flex min-w-0 flex-col gap-4">
                <ProgressIndicator 
                  progress={progress} 
                  status={processingStatus}
                  currentFile={currentFile}
                />
                <button
                  onClick={handleProcess}
                  disabled={!canProcess}
                  className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white shadow-md transition duration-smooth hover:-translate-y-[1px] hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                >
                  {converting ? 'Processing...' : 'Process Files'}
                </button>
                {toast && (
                  <ToastMessage
                    title={toast.type === 'success' ? 'Success' : toast.type === 'error' ? 'Error' : 'Info'}
                    message={toast.message}
                    tone={toast.type}
                  />
                )}
              </div>
            </section>
          </main>
        </div>
      </div>

      {/* Error Modal */}
      <ErrorModal 
        isOpen={errorFiles.length > 0}
        errorFiles={errorFiles}
        onClose={() => setErrorFiles([])}
      />
    </div>
  );
}
