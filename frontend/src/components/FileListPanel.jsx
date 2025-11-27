import React from 'react';
import { FiTrash2, FiX } from 'react-icons/fi';
import { cn } from '../utils/cn';
import { designTokens } from '../utils/theme';

const statusTone = {
  pending: 'bg-white/60 text-slate-800 dark:bg-white/10 dark:text-slate-100',
  processing: 'bg-accent/10 text-accent dark:bg-accent/15 dark:text-accent',
  done: 'bg-emerald-500/15 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-200',
  error: 'bg-red-500/15 text-red-600 dark:bg-red-400/15 dark:text-red-200',
};

export function FileListPanel({ files = [], onClearAll, onRemoveFile }) {
  return (
    <div
      className="glass-surface relative overflow-hidden rounded-card border border-slate-200 bg-white p-4 shadow-soft transition duration-smooth dark:border-white/10 dark:bg-white/5"
      style={{
        backdropFilter: `blur(${designTokens.blur})`,
        WebkitBackdropFilter: `blur(${designTokens.blur})`,
      }}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Session</p>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Files in queue</h3>
        </div>
        {files.length > 0 && (
          <button
            type="button"
            onClick={onClearAll}
            className="inline-flex items-center gap-2 rounded-full bg-red-500/10 px-4 py-2 text-xs font-semibold text-red-600 shadow-md transition duration-smooth hover:-translate-y-[1px] hover:bg-red-500/20 hover:shadow-lg dark:bg-red-500/20 dark:text-red-400"
          >
            <FiTrash2 className="h-3.5 w-3.5" />
            Clear All
          </button>
        )}
      </div>

      <div className="space-y-3 overflow-hidden rounded-2xl border border-white/40 bg-white/30 p-3 dark:border-white/5 dark:bg-white/5">
        {files.length === 0 ? (
          <div className="flex items-center justify-between rounded-xl bg-white/60 px-4 py-3 text-sm text-slate-600 shadow-inner dark:bg-white/5 dark:text-slate-300">
            <span>No files yet. Drop audio here to start.</span>
            <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">Idle</span>
          </div>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
            {files.map((file, index) => (
              <article
                key={file.id || index}
                className="group flex items-center gap-4 rounded-xl border border-white/60 bg-white/70 px-4 py-3 text-sm text-slate-800 shadow-sm transition duration-smooth hover:-translate-y-[1px] hover:shadow-lg dark:border-white/5 dark:bg-white/10 dark:text-slate-50"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-accent/80 to-accent text-white shadow-md">
                  <span className="text-sm font-semibold">{file.format}</span>
                </div>
                <div className="flex flex-1 items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold leading-5">{file.name}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {file.duration} • {file.size}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'rounded-full px-3 py-1 text-xs font-semibold shadow-sm transition duration-smooth',
                        statusTone[file.status] || 'bg-white/50 text-slate-700 dark:bg-white/10 dark:text-slate-200',
                      )}
                    >
                      {file.status === 'pending' && 'Pending'}
                      {file.status === 'processing' && 'Processing'}
                      {file.status === 'done' && 'Done'}
                      {file.status === 'error' && 'Error'}
                    </span>
                    {file.status !== 'processing' && onRemoveFile && (
                      <button
                        onClick={() => onRemoveFile(file.id || index)}
                        className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/10 text-red-600 opacity-0 transition duration-smooth hover:bg-red-500/20 group-hover:opacity-100 dark:text-red-400"
                        aria-label="Remove file"
                        title="Remove file"
                      >
                        <FiX className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
