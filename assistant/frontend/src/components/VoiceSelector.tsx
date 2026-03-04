import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api';

interface VoiceInfo {
  id: string;
  display: string;
  gender: 'female' | 'male';
  locale: string;
}

interface VoiceSelectorProps {
  voiceEn: string | null;
  voiceEs: string | null;
  onChangeEn: (voice: string) => void;
  onChangeEs: (voice: string) => void;
  disabled?: boolean;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  voiceEn,
  voiceEs,
  onChangeEn,
  onChangeEs,
  disabled = false,
}) => {
  const [voices, setVoices] = useState<Record<string, VoiceInfo[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioBlobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    loadVoices();
    return () => {
      // Cleanup audio on unmount
      audioRef.current?.pause();
      if (audioBlobUrlRef.current) URL.revokeObjectURL(audioBlobUrlRef.current);
    };
  }, []);

  const loadVoices = async () => {
    try {
      setLoading(true);
      const data = await api.getAvailableVoices();
      setVoices(data.voices || {});
      setError(null);
    } catch (err) {
      console.error('Failed to load voices:', err);
      setError('Failed to load available voices');
      setVoices({ en: [], es: [] });
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

  const renderSection = (
    langKey: string,
    selectedVoice: string | null,
    onChange: (v: string) => void,
    langLabel: string,
    defaultVoiceId: string,
  ) => {
    const voiceList: VoiceInfo[] = voices[langKey] || [];
    const effectiveVoice = selectedVoice || defaultVoiceId;

    return (
      <div className="voice-language-section">
        <div className="voice-lang-header">{langLabel}</div>
        <div className="voice-cards">
          {voiceList.map((voice) => {
            const isSelected = effectiveVoice === voice.id;
            const isPlaying = playingVoice === voice.id;
            const isLoadingThis = loadingPreview === voice.id;

            return (
              <div
                key={voice.id}
                className={`voice-card${isSelected ? ' selected' : ''}`}
                onClick={() => !disabled && onChange(voice.id)}
                role="radio"
                aria-checked={isSelected}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && !disabled && onChange(voice.id)}
              >
                <div className={`voice-gender-badge ${voice.gender}`}>
                  {voice.gender === 'female' ? '♀' : '♂'}
                </div>
                <div className="voice-card-info">
                  <span className="voice-name">{voice.display}</span>
                  <span className="voice-locale">{voice.locale}</span>
                </div>
                <button
                  className={`voice-preview-btn${isPlaying ? ' playing' : ''}${isLoadingThis ? ' loading' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePreview(voice.id);
                  }}
                  disabled={disabled || (loadingPreview !== null && loadingPreview !== voice.id)}
                  title={isPlaying ? 'Stop preview' : 'Preview voice'}
                >
                  {isLoadingThis ? '…' : isPlaying ? '■' : '▶'}
                </button>
                <input
                  className="voice-radio"
                  type="radio"
                  name={`voice-${langKey}`}
                  checked={isSelected}
                  onChange={() => onChange(voice.id)}
                  disabled={disabled}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (loading) return <div className="voice-selector"><span className="voice-loading">Loading voices…</span></div>;

  if (error) {
    return (
      <div className="voice-selector voice-selector-error">
        <p>{error}</p>
        <button className="btn-secondary" onClick={loadVoices}>Retry</button>
      </div>
    );
  }

  return (
    <div className="voice-selector">
      {renderSection('en', voiceEn, onChangeEn, 'English', 'en-US-AriaNeural')}
      {renderSection('es', voiceEs, onChangeEs, 'Spanish', 'es-MX-DaliaNeural')}
    </div>
  );
};

