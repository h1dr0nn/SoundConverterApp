import React from 'react';

export function ProgressIndicator({ progress, status, currentFile }) {
  const progressPercent = Math.min(100, Math.max(0, progress || 0));

  return (
    <div className="space-y-3 rounded-card border border-slate-200 bg-white p-5 shadow-soft transition duration-smooth dark:border-white/10 dark:bg-white/10">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Progress</p>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {status || 'Idle'}
          </h3>
        </div>
        <span className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-md">
          {progressPercent.toFixed(0)}%
        </span>
      </div>

      {currentFile && (
        <div className="min-w-0">
          <p className="truncate text-xs text-slate-600 dark:text-slate-300" title={currentFile}>
            Processing: {currentFile.split(/[/\\]/).pop()}
          </p>
        </div>
      )}

      <div className="overflow-hidden rounded-full bg-white/60 shadow-inner dark:bg-white/5">
        <div
          className="h-3 rounded-full bg-gradient-to-r from-accent/80 to-accent shadow-sm transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        {progressPercent === 0 && 'Ready to process'}
        {progressPercent > 0 && progressPercent < 100 && 'Processing files...'}
        {progressPercent === 100 && 'Complete!'}
      </p>
    </div>
  );
}
