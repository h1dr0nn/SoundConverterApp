import React, { useState } from 'react';
import { FiArrowLeft, FiSettings, FiSliders, FiSun, FiMoon, FiInfo } from 'react-icons/fi';
import { designTokens } from '../utils/theme';
import { useTheme } from '../hooks/useTheme';
import { useSettingsContext } from '../context/SettingsContext';

export function SettingsPage({ onBack}) {
  const { theme, toggleTheme } = useTheme();
  const { settings } = useSettingsContext();
  const [activeTab, setActiveTab] = useState('configuration');

  const tabs = [
    { id: 'configuration', label: 'Configuration', icon: FiSettings },
    { id: 'advanced', label: 'Advanced', icon: FiSliders },
    { id: 'appearance', label: 'Appearance', icon: theme === 'dark' ? FiMoon : FiSun },
    { id: 'about', label: 'About', icon: FiInfo }
  ];

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100/80 to-slate-50 px-4 py-10 text-slate-900 transition duration-smooth dark:from-[#101012] dark:via-[#141418] dark:to-[#0f0f12] dark:text-slate-100"
      style={{ fontFamily: designTokens.font }}
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        {/* Header */}
        <header className="flex items-center gap-4 rounded-card border border-slate-200/80 bg-white/85 p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth dark:border-white/10 dark:bg-white/10">
          <button
            onClick={onBack}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200/80 bg-white/90 shadow-md transition duration-smooth hover:-translate-y-[1px] hover:shadow-lg dark:border-white/10 dark:bg-white/10"
            aria-label="Back to home"
          >
            <FiArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">Application</p>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Settings</h1>
          </div>
        </header>

        {/* Tab Bar */}
        <div className="rounded-card border border-slate-200/80 bg-white/85 shadow-soft backdrop-blur-[32px] transition duration-smooth dark:border-white/10 dark:bg-white/10">
          <div className="flex gap-2 border-b border-slate-200 p-2 dark:border-white/10">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition duration-smooth ${
                    activeTab === tab.id
                      ? 'bg-accent text-white shadow-md'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'configuration' && <ConfigurationTab />}
            {activeTab === 'advanced' && <AdvancedTab />}
            {activeTab === 'appearance' && <AppearanceTab theme={theme} toggleTheme={toggleTheme} />}
            {activeTab === 'about' && <AboutTab />}
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigurationTab() {
  const { settings, updateSetting } = useSettingsContext();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">General Configuration</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure default settings for audio processing
        </p>
      </div>

      <div className="space-y-4">
        {/* Default Output Format */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Default Output Format</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Format to pre-select when converting files
            </p>
          </div>
          <select
            value={settings.defaultFormat}
            onChange={(e) => updateSetting('defaultFormat', e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 transition focus:outline-none focus:ring-2 focus:ring-accent dark:border-white/10 dark:bg-white/10 dark:text-slate-100"
          >
            <option>AAC</option>
            <option>MP3</option>
            <option>WAV</option>
            <option>FLAC</option>
            <option>OGG</option>
            <option>M4A</option>
          </select>
        </div>

        {/* Default Output Location */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Default Output Location</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Where to save processed files by default
            </p>
          </div>
          <select
            value={settings.outputLocation}
            onChange={(e) => updateSetting('outputLocation', e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 transition focus:outline-none focus:ring-2 focus:ring-accent dark:border-white/10 dark:bg-white/10 dark:text-slate-100"
          >
            <option>Same as source</option>
            <option>Ask every time</option>
            <option>Custom folder</option>
          </select>
        </div>

        {/* Auto-clear completed files */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Auto-clear Completed Files</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Automatically remove files from queue after processing
            </p>
          </div>
          <button
            onClick={() => updateSetting('autoClear', !settings.autoClear)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.autoClear ? 'bg-accent' : 'bg-slate-300 dark:bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform ${
                settings.autoClear ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Desktop Notifications */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Desktop Notifications</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Show system notifications when processing completes
            </p>
          </div>
          <button
            onClick={() => updateSetting('notifications', !settings.notifications)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.notifications ? 'bg-accent' : 'bg-slate-300 dark:bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform ${
                settings.notifications ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}

function AdvancedTab() {
  const { settings, updateSetting } = useSettingsContext();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Advanced Settings</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Fine-tune performance and processing behavior
        </p>
      </div>

      <div className="space-y-4">
        {/* Concurrent Processing */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Concurrent File Processing</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Number of files to process simultaneously
            </p>
          </div>
          <select
            value={settings.concurrentFiles}
            onChange={(e) => updateSetting('concurrentFiles', e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 transition focus:outline-none focus:ring-2 focus:ring-accent dark:border-white/10 dark:bg-white/10 dark:text-slate-100"
          >
            <option value="1">1 (Sequential)</option>
            <option value="2">2 (Balanced)</option>
            <option value="4">4 (Fast)</option>
            <option value="8">8 (Maximum)</option>
          </select>
        </div>

        {/* Max File Size */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="mb-3">
            <p className="font-semibold text-slate-900 dark:text-white">Maximum File Size</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Maximum size per file (MB) - larger files will be rejected
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min="100"
              max="2000"
              step="100"
              value={settings.maxFileSize}
              onChange={(e) => updateSetting('maxFileSize', e.target.value)}
              className="h-2 flex-1 appearance-none rounded-full bg-slate-200 dark:bg-white/10"
            />
            <span className="min-w-[60px] text-right text-sm font-semibold text-slate-800 dark:text-slate-100">
              {settings.maxFileSize} MB
            </span>
          </div>
        </div>

        {/* Debug Logging */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Enable Debug Logging</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Log detailed processing information for troubleshooting
            </p>
          </div>
          <button
            onClick={() => updateSetting('enableLogging', !settings.enableLogging)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.enableLogging ? 'bg-accent' : 'bg-slate-300 dark:bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform ${
                settings.enableLogging ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* FFmpeg Version Info */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <p className="font-semibold text-slate-900 dark:text-white">FFmpeg Backend</p>
          <p className="mt-2 font-mono text-xs text-slate-600 dark:text-slate-400">
            Version: 6.1.1 (bundled)
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Using embedded FFmpeg for audio processing
          </p>
        </div>
      </div>
    </div>
  );
}

function AppearanceTab({ theme, toggleTheme }) {
  const { settings, updateSetting } = useSettingsContext();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Appearance</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Customize the visual appearance of the application
        </p>
      </div>

      <div className="space-y-4">
        {/* Theme Toggle */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Theme</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Switch between light and dark mode
            </p>
          </div>
          
          <button
            onClick={toggleTheme}
            className="relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 bg-gradient-to-r from-orange-400 to-orange-500"
            style={{
              background: theme === 'dark' 
                ? 'linear-gradient(to right, #1e293b, #334155)'
                : 'linear-gradient(to right, #fb923c, #f97316)'
            }}
          >
            <span className="sr-only">Toggle theme</span>
            <span
              className={`inline-flex h-6 w-6 transform items-center justify-center rounded-full bg-white shadow-lg transition-transform ${
                theme === 'dark' ? 'translate-x-9' : 'translate-x-1'
              }`}
            >
              {theme === 'dark' ? (
                <FiMoon className="h-3.5 w-3.5 text-slate-700" />
              ) : (
                <FiSun className="h-3.5 w-3.5 text-orange-500" />
              )}
            </span>
          </button>
        </div>

        {/* Accent Color */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="font-semibold text-slate-900 dark:text-white">Accent Color</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Primary color for buttons and highlights
              </p>
            </div>
            <div className="flex gap-2">
              {['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#5856D6', '#AF52DE'].map(color => (
                <button
                  key={color}
                  onClick={() => updateSetting('accentColor', color)}
                  className={`h-8 w-8 rounded-full transition-all hover:scale-110 ${
                    settings.accentColor === color ? 'ring-2 ring-offset-2 ring-slate-400 dark:ring-slate-300' : ''
                  }`}
                  style={{ backgroundColor: color }}
                  aria-label={`Set accent color to ${color}`}
                  title={color}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Font Size */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
          <div className="flex-1">
            <p className="font-semibold text-slate-900 dark:text-white">Font Size</p>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Adjust text size throughout the application
            </p>
          </div>
          <select
            value={settings.fontSize}
            onChange={(e) => updateSetting('fontSize', e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 transition focus:outline-none focus:ring-2 focus:ring-accent dark:border-white/10 dark:bg-white/10 dark:text-slate-100"
          >
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
          </select>
        </div>
      </div>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Sound Converter</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">Version 0.1.0</p>
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Built with</span>
          <span className="text-sm text-slate-600 dark:text-slate-300">Tauri + React + Python</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Backend</span>
          <span className="text-sm text-slate-600 dark:text-slate-300">FFmpeg + pydub</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">License</span>
          <span className="text-sm text-slate-600 dark:text-slate-300">MIT</span>
        </div>
        <div className="flex items-center justify-between border-t border-slate-200 pt-3 dark:border-white/10">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Created by</span>
          <span className="text-sm font-bold text-accent">h1dr0n</span>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Features</h4>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <li className="flex items-start gap-2">
            <span className="text-accent">•</span>
            <span>Convert audio files between multiple formats</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent">•</span>
            <span>Master audio with professional presets</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent">•</span>
            <span>Trim silence automatically from recordings</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent">•</span>
            <span>Batch processing for multiple files</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
