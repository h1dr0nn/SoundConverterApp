import React, { useState } from 'react';
import { cn } from '../utils/cn';

const PRESETS = {
  Music: {
    label: 'Music',
    description: 'Optimized for music tracks',
    target_lufs: -12.0,
    apply_compression: true,
    apply_limiter: true,
    output_gain: 0.0
  },
  Podcast: {
    label: 'Podcast',
    description: 'Clear speech with warmth',
    target_lufs: -16.0,
    apply_compression: true,
    apply_limiter: true,
    output_gain: 1.5
  },
  'Voice-over': {
    label: 'Voice-over',
    description: 'Professional narration',
    target_lufs: -18.0,
    apply_compression: true,
    apply_limiter: true,
    output_gain: 0.5
  }
};

export function MasterControls({ preset, onPresetChange, parameters, onParametersChange }) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handlePresetChange = (newPreset) => {
    onPresetChange(newPreset);
    // Update parameters based on preset
    if (PRESETS[newPreset]) {
      onParametersChange({
        target_lufs: PRESETS[newPreset].target_lufs,
        apply_compression: PRESETS[newPreset].apply_compression,
        apply_limiter: PRESETS[newPreset].apply_limiter,
        output_gain: PRESETS[newPreset].output_gain
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Preset Selector */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          Master Preset
        </label>
        <div className="grid gap-2">
          {Object.entries(PRESETS).map(([key, config]) => (
            <button
              key={key}
              onClick={() => handlePresetChange(key)}
              className={cn(
                'flex items-start gap-3 rounded-xl border-2 p-3 text-left transition duration-smooth',
                preset === key
                  ? 'border-accent bg-accent/10 dark:bg-accent/20'
                  : 'border-white/40 bg-white/30 hover:border-white/60 hover:bg-white/50 dark:border-white/10 dark:bg-white/5 dark:hover:border-white/20'
              )}
            >
              <div className="flex-1">
                <p className={cn(
                  'text-sm font-semibold',
                  preset === key ? 'text-accent' : 'text-slate-800 dark:text-slate-100'
                )}>
                  {config.label}
                </p>
                <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-300">
                  {config.description}
                </p>
              </div>
              {preset === key && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-white">
                  <span className="text-xs">✓</span>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex w-full items-center justify-between rounded-xl border border-white/40 bg-white/30 px-4 py-2.5 text-sm font-semibold text-slate-700 transition duration-smooth hover:bg-white/50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
      >
        <span>Advanced Parameters</span>
        <span className={cn('transition-transform duration-smooth', showAdvanced && 'rotate-180')}>▼</span>
      </button>

      {/* Advanced Parameters */}
      {showAdvanced && (
        <div className="space-y-4 rounded-2xl border border-white/40 bg-white/20 p-4 dark:border-white/10 dark:bg-white/5">
          {/* Target LUFS */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                Target LUFS
              </label>
              <span className="text-xs text-slate-600 dark:text-slate-300">
                {parameters.target_lufs.toFixed(1)} dB
              </span>
            </div>
            <input
              type="range"
              min="-24"
              max="-6"
              step="0.5"
              value={parameters.target_lufs}
              onChange={(e) => onParametersChange({ ...parameters, target_lufs: parseFloat(e.target.value) })}
              className="h-2 w-full appearance-none rounded-full bg-white/50 dark:bg-white/10"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Loudness normalization level (lower = quieter)
            </p>
          </div>

          {/* Compression Toggle */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">Apply Compression</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Reduce dynamic range</p>
            </div>
            <button
              onClick={() => onParametersChange({ ...parameters, apply_compression: !parameters.apply_compression })}
              className={cn(
                'relative h-6 w-11 rounded-full transition duration-smooth',
                parameters.apply_compression ? 'bg-accent' : 'bg-slate-300 dark:bg-slate-600'
              )}
            >
              <div className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-smooth',
                parameters.apply_compression ? 'translate-x-5' : 'translate-x-0.5'
              )} />
            </button>
          </div>

          {/* Limiter Toggle */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">Apply Limiter</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Prevent clipping</p>
            </div>
            <button
              onClick={() => onParametersChange({ ...parameters, apply_limiter: !parameters.apply_limiter })}
              className={cn(
                'relative h-6 w-11 rounded-full transition duration-smooth',
                parameters.apply_limiter ? 'bg-accent' : 'bg-slate-300 dark:bg-slate-600'
              )}
            >
              <div className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-smooth',
                parameters.apply_limiter ? 'translate-x-5' : 'translate-x-0.5'
              )} />
            </button>
          </div>

          {/* Output Gain */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                Output Gain
              </label>
              <span className="text-xs text-slate-600 dark:text-slate-300">
                {parameters.output_gain > 0 ? '+' : ''}{parameters.output_gain.toFixed(1)} dB
              </span>
            </div>
            <input
              type="range"
              min="-6"
              max="6"
              step="0.5"
              value={parameters.output_gain}
              onChange={(e) => onParametersChange({ ...parameters, output_gain: parseFloat(e.target.value) })}
              className="h-2 w-full appearance-none rounded-full bg-white/50 dark:bg-white/10"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Final volume boost or reduction
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
