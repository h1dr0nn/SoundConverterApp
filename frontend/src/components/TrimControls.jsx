import React from 'react';

export function TrimControls({ threshold, onThresholdChange, minSilence, onMinSilenceChange, padding, onPaddingChange }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          Silence Detection
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure how silence is detected and removed from your audio files.
        </p>
      </div>

      {/* Silence Threshold */}
      <div className="space-y-2 rounded-xl border border-white/40 bg-white/30 p-4 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            Silence Threshold
          </label>
          <span className="text-xs text-slate-600 dark:text-slate-300">
            {threshold.toFixed(1)} dB
          </span>
        </div>
        <input
          type="range"
          min="-60"
          max="-30"
          step="1"
          value={threshold}
          onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
          className="h-2 w-full appearance-none rounded-full bg-white/50 dark:bg-white/10"
        />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Audio below this level is considered silence. Lower = more aggressive trimming.
        </p>
      </div>

      {/* Minimum Silence Duration */}
      <div className="space-y-2 rounded-xl border border-white/40 bg-white/30 p-4 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            Minimum Silence Duration
          </label>
          <span className="text-xs text-slate-600 dark:text-slate-300">
            {minSilence} ms
          </span>
        </div>
        <input
          type="range"
          min="100"
          max="2000"
          step="50"
          value={minSilence}
          onChange={(e) => onMinSilenceChange(parseInt(e.target.value))}
          className="h-2 w-full appearance-none rounded-full bg-white/50 dark:bg-white/10"
        />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Only silence longer than this duration will be trimmed.
        </p>
      </div>

      {/* Padding */}
      <div className="space-y-2 rounded-xl border border-white/40 bg-white/30 p-4 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
            Padding
          </label>
          <span className="text-xs text-slate-600 dark:text-slate-300">
            {padding} ms
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="1000"
          step="50"
          value={padding}
          onChange={(e) => onPaddingChange(parseInt(e.target.value))}
          className="h-2 w-full appearance-none rounded-full bg-white/50 dark:bg-white/10"
        />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Keep this amount of silence at the beginning and end for natural fades.
        </p>
      </div>

      {/* Example Visual */}
      <div className="rounded-xl border border-accent/30 bg-accent/5 p-4 dark:border-accent/20 dark:bg-accent/10">
        <p className="mb-2 text-xs font-semibold text-accent">Example</p>
        <div className="flex items-center gap-2">
          <div className="h-8 w-3 rounded-sm bg-slate-300 dark:bg-slate-600" title="Trimmed silence" />
          {padding > 0 && <div className="h-6 w-2 rounded-sm bg-accent/30" title="Padding" />}
          <div className="h-12 flex-1 rounded-sm bg-accent" title="Audio content" />
          {padding > 0 && <div className="h-6 w-2 rounded-sm bg-accent/30" title="Padding" />}
          <div className="h-8 w-3 rounded-sm bg-slate-300 dark:bg-slate-600" title="Trimmed silence" />
        </div>
        <div className="mt-2 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Silence removed</span>
          <span>Audio kept</span>
          <span>Silence removed</span>
        </div>
      </div>
    </div>
  );
}
