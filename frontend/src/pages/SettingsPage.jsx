import React from 'react';
import { FiArrowLeft, FiSettings, FiSliders, FiSun, FiMoon, FiInfo } from 'react-icons/fi';
import { designTokens } from '../utils/theme';
import { useTheme } from '../hooks/useTheme';

export function SettingsPage({ onBack }) {
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = React.useState('configuration');

  const tabs = [
    { id: 'configuration', label: 'Configuration', icon: FiSettings },
    { id: 'advanced', label: 'Advanced', icon: FiSliders },
    { id: 'appearance', label: 'Appearance', icon: theme === 'dark' ? FiMoon : FiSun },
    { id: 'about', label: 'About', icon: FiInfo }
  ];

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50 px-4 py-10 text-slate-900 transition duration-smooth dark:from-[#101012] dark:via-[#141418] dark:to-[#0f0f12] dark:text-slate-100"
      style={{ fontFamily: designTokens.font }}
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        {/* Header */}
        <header className="flex items-center gap-4 rounded-card border border-slate-200 bg-white p-5 shadow-soft backdrop-blur-[32px] transition duration-smooth dark:border-white/10 dark:bg-white/10">
          <button
            onClick={onBack}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white shadow-md transition duration-smooth hover:-translate-y-[1px] hover:shadow-lg dark:border-white/10 dark:bg-white/10"
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
        <div className="rounded-card border border-slate-200 bg-white shadow-soft backdrop-blur-[32px] transition duration-smooth dark:border-white/10 dark:bg-white/10">
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
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">General Configuration</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure general application settings and preferences.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center dark:border-white/10 dark:bg-white/5">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No configuration options available yet. This section will be populated with settings in future updates.
        </p>
      </div>
    </div>
  );
}

function AdvancedTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Advanced Settings</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Advanced configuration options for power users.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center dark:border-white/10 dark:bg-white/5">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No advanced settings available yet. This section will be populated in future updates.
        </p>
      </div>
    </div>
  );
}

function AppearanceTab({ theme, toggleTheme }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">Appearance</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Customize the visual appearance of the application.
        </p>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-6 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center justify-between">
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
