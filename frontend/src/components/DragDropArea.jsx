import React from 'react';
import { designTokens } from '../utils/theme';

export function DragDropArea() {
  return (
    <div
      className="relative flex flex-col items-center justify-center rounded-card border border-white/60 bg-white/50 p-10 shadow-soft backdrop-blur"
      style={{
        backdropFilter: `blur(${designTokens.blur})`,
        WebkitBackdropFilter: `blur(${designTokens.blur})`,
      }}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/70 shadow-md">
        <span className="text-3xl" role="img" aria-label="sparkles">
          ✨
        </span>
      </div>
      <p className="mt-6 text-lg font-semibold text-slate-800">Drop your audio files</p>
      <p className="mt-2 max-w-xs text-center text-sm text-slate-600">
        Drag and drop files here to prepare for conversion. We will keep things lightweight and
        responsive, just like a native macOS app.
      </p>
      <div className="mt-6 rounded-full bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 shadow">
        Drag & Drop Placeholder
      </div>
    </div>
  );
}
