import { useState, useEffect } from 'react';

const STORAGE_KEY = 'soundconverter_settings';

const DEFAULT_SETTINGS = {
  // Configuration
  defaultFormat: 'AAC',
  outputLocation: 'Same as source',
  customOutputFolder: '',
  autoClear: false,
  notifications: true,
  
  // Advanced
  concurrentFiles: '2',
  maxFileSize: '500',
  enableLogging: false,
  
  // Appearance
  accentColor: '#007AFF',
  fontSize: 'medium',
};

export function useSettings() {
  const [settings, setSettings] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
    return DEFAULT_SETTINGS;
  });

  // Save to localStorage whenever settings change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }, [settings]);

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const updateSettings = (updates) => {
    setSettings(prev => ({ ...prev, ...updates }));
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
  };

  return {
    settings,
    updateSetting,
    updateSettings,
    resetSettings,
  };
}
