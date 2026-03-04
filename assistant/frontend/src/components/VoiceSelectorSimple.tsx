import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './VoiceSelectorSimple.css';

interface VoiceInfo {
  id: string;
  display: string;
  gender: 'female' | 'male';
  locale: string;
}

interface VoiceSelectorSimpleProps {
  language: 'en' | 'es';
  selectedVoice: string | null;
  onSelect: (voiceId: string) => void;
  disabled?: boolean;
}

export const VoiceSelectorSimple: React.FC<VoiceSelectorSimpleProps> = ({
  language,
  selectedVoice,
  onSelect,
  disabled = false,
}) => {
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    loadVoices();
    return () => {
      audioRef.current?.pause();
      if (audioBlobUrlRef.current) URL.revokeObjectURL(audioBlobUrlRef.current);
    };
  }, []);

  const loadVoices = async () => {
    try {
      setLoading(true);
      const data = await api.getAvailableVoices();
      const languageKey = language === 'es' ? 'es' : 'en';
      setVoices(data.voices?.[languageKey] || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load voices:', err);
      setError('Failed to load available voices');
      setVoices([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (voiceId: string) => {
    // Stop any playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioBlobUrlRef.current) {
      URL.revokeObjectURL(audioBlobUrlRef.current);
      audioBlobUrlRef.current = null;
    }

    if (playingVoice === voiceId) {
      setPlayingVoice(null);
      return;
    }

    try {
      setLoadingPreview(voiceId);
      const blob = await api.previewVoice(voiceId);
      const url = URL.createObjectURL(blob);
      audioBlobUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setPlayingVoice(null);
        if (audioBlobUrlRef.current) {
          URL.revokeObjectURL(audioBlobUrlRef.current);
          audioBlobUrlRef.current = null;
        }
      };
      audio.onerror = () => {
        setPlayingVoice(null);
      };

      setPlayingVoice(voiceId);
      await audio.play();
    } catch (err) {
      console.error('Voice preview failed:', err);
      setPlayingVoice(null);
    } finally {
      setLoadingPreview(null);
    }
  };

  if (loading) {
    return <div className="voice-selector-simple">Loading voices...</div>;
  }

  if (error) {
    return <div className="voice-selector-simple error">{error}</div>;
  }

  const langLabel = language === 'es' ? 'Spanish' : 'English';
  const selectedVoiceInfo = voices.find((v) => v.id === selectedVoice);

  return (
    <div className="voice-selector-simple">
      <label className="voice-label">{langLabel}</label>
      <div className="voice-selector-container">
        <select
          value={selectedVoice || ''}
          onChange={(e) => onSelect(e.target.value)}
          disabled={disabled || voices.length === 0}
          className="voice-select"
        >
          <option value="">-- Select {langLabel} Voice --</option>
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.display} ({voice.gender})
            </option>
          ))}
        </select>
        {selectedVoiceInfo && (
          <button
            className={`voice-preview-btn ${playingVoice === selectedVoice ? 'playing' : ''}`}
            onClick={() => handlePreview(selectedVoice!)}
            disabled={disabled || loadingPreview === selectedVoice}
            title={playingVoice === selectedVoice ? 'Stop preview' : 'Preview voice'}
          >
            {loadingPreview === selectedVoice ? '⏳' : playingVoice === selectedVoice ? '⏹' : '▶'}
          </button>
        )}
      </div>
    </div>
  );
};
