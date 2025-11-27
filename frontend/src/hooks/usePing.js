import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

export function usePing() {
  const [status, setStatus] = useState('Idle');
  const [lastResponse, setLastResponse] = useState('');

  const ping = useCallback(async () => {
    setStatus('Pinging...');
    try {
      const response = await invoke('ping');
      setLastResponse(response);
      setStatus('Online');
    } catch (error) {
      console.error('Ping failed', error);
      setStatus('Error');
    }
  }, []);

  return { status, lastResponse, ping };
}
