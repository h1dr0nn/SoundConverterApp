import React, { useState } from 'react';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  const [currentPage, setCurrentPage] = useState('home'); // 'home' | 'settings'

  return currentPage === 'home' ? (
    <HomePage onOpenSettings={() => setCurrentPage('settings')} />
  ) : (
    <SettingsPage onBack={() => setCurrentPage('home')} />
  );
}

export default App;
