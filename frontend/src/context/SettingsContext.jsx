import React, { createContext, useContext, useEffect } from 'react';
import { useSettings } from '../hooks/useSettings';

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const settingsValue = useSettings();
  const { settings } = settingsValue;

  // Apply accent color to CSS variable
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--accent-color', settings.accentColor);
    // Force repaint to ensure immediate update
    root.style.display = 'none';
    root.offsetHeight; // trigger reflow
    root.style.display = '';
  }, [settings.accentColor]);

  // Apply text size scaling via CSS variables (decoupled from layout)
  useEffect(() => {
    const root = document.documentElement;
    
    // Base sizes in rem (Default: Medium)
    const baseSizes = {
      '--text-xs': 0.75,
      '--text-sm': 0.875,
      '--text-base': 1,
      '--text-lg': 1.125,
      '--text-xl': 1.25,
      '--text-2xl': 1.5,
      '--text-3xl': 1.875,
      '--text-4xl': 2.25,
    };

    // Scaling factors
    const scales = {
      small: 0.875,   // ~14px equivalent
      medium: 1,      // ~16px equivalent
      large: 1.125    // ~18px equivalent
    };

    const scale = scales[settings.fontSize] || 1;

    Object.entries(baseSizes).forEach(([variable, value]) => {
      root.style.setProperty(variable, `${value * scale}rem`);
    });
  }, [settings.fontSize]);

  return (
    <SettingsContext.Provider value={settingsValue}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettingsContext() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettingsContext must be used within SettingsProvider');
  }
  return context;
}
