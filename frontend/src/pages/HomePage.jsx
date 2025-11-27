import React from 'react';
import { DragDropArea } from '../components/DragDropArea';
import { usePing } from '../hooks/usePing';
import { designTokens } from '../utils/theme';

export function HomePage() {
  const { status, lastResponse, ping } = usePing();

  return (
    <div
      className="flex min-h-screen flex-col items-center bg-gradient-to-br from-white/90 to-background p-6 text-slate-900"
      style={{
        fontFamily: designTokens.font,
      }}
    >
      <header className="mb-10 w-full max-w-5xl rounded-card border border-white/60 bg-white/60 px-6 py-4 shadow-soft backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Sound Converter</p>
            <h1 className="text-2xl font-semibold text-slate-900">Foundation Setup</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white shadow-md">
              macOS style
            </span>
            <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-slate-700 shadow">
              {status}
            </span>
          </div>
        </div>
      </header>

      <main className="flex w-full max-w-5xl flex-col gap-8">
        <section className="rounded-card border border-white/60 bg-white/60 p-8 shadow-soft backdrop-blur">
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
            <div className="space-y-3 md:max-w-md">
              <h2 className="text-xl font-semibold text-slate-900">Drop Zone</h2>
              <p className="text-sm text-slate-600">
                Drag your audio files into the placeholder. We will wire up the conversion flow in the next
                phase.
              </p>
              <button
                type="button"
                onClick={ping}
                className="inline-flex items-center justify-center rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white shadow-md transition duration-smooth hover:scale-[1.01] hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Send Ping
              </button>
              {lastResponse ? (
                <p className="text-sm text-slate-700">Tauri says: {lastResponse}</p>
              ) : null}
            </div>
            <div className="flex-1">
              <DragDropArea />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
