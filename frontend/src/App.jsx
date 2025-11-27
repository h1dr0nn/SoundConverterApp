import React, { useState } from 'react';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import { SettingsProvider } from './context/SettingsContext';

export default function App() {
  const [currentPage, setCurrentPage] = useState('home');
  
  // Lifted state to persist across navigation
  const [files, setFiles] = useState([]);
  const [outputFolder, setOutputFolder] = useState('');

  return (
    <SettingsProvider>
      {currentPage === 'home' ? (
        <HomePage 
          onOpenSettings={() => setCurrentPage('settings')} 
          files={files}
          setFiles={setFiles}
          outputFolder={outputFolder}
          setOutputFolder={setOutputFolder}
        />
      ) : (
        <SettingsPage onBack={() => setCurrentPage('home')} />
      )}
    </SettingsProvider>
  );
}
