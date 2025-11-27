import React, { useState, useEffect } from 'react';
import { FiSettings } from 'react-icons/fi';
import { listen } from '@tauri-apps/api/event';
import { dirname } from '@tauri-apps/api/path';
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
import { getFileMetadata } from '../utils/audioUtils';
import { notifySuccess, notifyError } from '../utils/notifications';

const formatOptions = ['AAC', 'MP3', 'WAV', 'FLAC', 'OGG', 'M4A'];

export function HomePage({ onOpenSettings }) {
  const { theme } = useTheme();
  const { convert, loading: converting } = useConvertAudio();

  // Mode state
  const [mode, setMode] = useState('convert'); // 'convert' | 'master' | 'trim'

  // File management
  const [files, setFiles] = useState([]);
  const [outputFolder, setOutputFolder] = useState('');

  // Convert mode
  const [selectedFormat, setSelectedFormat] = useState('AAC');

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

  // Handle files added from drag & drop or file picker
  const handleFilesAdded = async (newFiles) => {
    try {
      const fileMetadataPromises = newFiles.map(file => getFileMetadata(file));
      const fileMetadata = await Promise.all(fileMetadataPromises);

      // Auto-fill output folder from first file if not set
      if (files.length === 0 && newFiles.length > 0 && !outputFolder) {
        try {
          const firstFilePath = newFiles[0].path || newFiles[0].name;
          const dir = await dirname(firstFilePath);
          setOutputFolder(dir);
        } catch (error) {
          console.error('Failed to get directory:', error);
        }
      }

      setFiles(prev => [...prev, ...fileMetadata]);
      setToast({ type: 'info', message: `Added ${newFiles.length} file(s) to queue` });
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

  // Build payload for backend based on mode
  const buildPayload = () => {
    const filePaths = files.map(f => f.path);

    const basePayload = {
      files: filePaths,
      output: outputFolder || './'
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
        input_paths: filePaths,
        output_directory: outputFolder || './',
        preset: masterPreset,
        parameters: masterParams
      };
    } else if (mode === 'trim') {
      return {
        operation: 'trim',
        input_paths: filePaths,
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
      // Reset all files to pending
      setFiles(prev => prev.map(f => ({ ...f, status: 'pending', error: null, output: null })));
      setProgress(0);
      setProcessingStatus('Starting...');
      setErrorFiles([]);

      const payload = buildPayload();
      await convert(payload);

    } catch (error) {
      console.error('Processing error:', error);
      setToast({ type: 'error', message: error.message || 'Processing failed' });
      await notifyError('Processing Failed', error.message || 'An error occurred');
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
            notifySuccess('Processing Complete', `${files.length} file(s) processed successfully`);
          } else {
            // Check for errors in files
            const failedFiles = files.filter((f, i) => {
              // If we have error info from backend, use it
              return !outputs || !outputs[i];
            }).map(f => ({ ...f, error: 'Processing failed' }));

            if (failedFiles.length > 0) {
              setErrorFiles(failedFiles);
            }

            setProgress(100);
            setProcessingStatus('Completed with errors');
            notifyError('Processing Errors', `${failedFiles.length} file(s) failed`);
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

  const canProcess = files.length > 0 && outputFolder && !converting;

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
            <section className={`grid gap-4 rounded-card border ${themeClasses.card} p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth lg:grid-cols-[1.15fr,0.85fr]`}>
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
            <section className={`grid gap-4 rounded-card border ${themeClasses.card} p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth lg:grid-cols-[1.1fr,0.9fr]`}>
              <FileListPanel 
                files={files} 
                onClearAll={handleClearAll}
                onRemoveFile={handleRemoveFile}
              />
              <div className="flex flex-col gap-4">
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
