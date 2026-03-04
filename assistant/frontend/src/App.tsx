import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ChatPanel, Message } from './components/ChatPanel';
import { AvatarStage } from './components/AvatarStage';
import { SettingsPage } from './pages/SettingsPage';
import { api, ChatResponse, AnimationPayload } from './api';
import './App.css';

interface AppState {
  sessionId: string;
  messages: Message[];
  currentAnimation?: AnimationPayload;
  isLoading: boolean;
  error?: string;
  audioUrl?: string;
  isPlaying: boolean;
  audioStartTime: number;
  audioDurationSeconds?: number;
  volume: number;  // 0 to 1
  voiceDebug?: {
    requestLanguage: string;
    audioLanguage?: string;
    voiceId?: string;
    durationSeconds?: number;
    artifactId?: string;
    wavPath?: string;
    encodingOk: boolean;
    glitchRequested?: boolean;
    glitchApplied?: boolean;
    glitchError?: string | null;
    glitchEffects?: string[];
    glitchIntensity?: number;
    fileSizeBefore?: number;
    fileSizeAfter?: number;
    mtimeBefore?: number;
    mtimeAfter?: number;
  };
  preferredSpriteId?: string;
}

interface LocalPreferencesCache {
  default_avatar?: string;
}

const detectInputLanguage = (text: string): 'es' | 'en' => {
  const normalized = text.normalize('NFC').toLowerCase();
  const spanishHints = [
    '¿',
    '¡',
    'ñ',
    'á',
    'é',
    'í',
    'ó',
    'ú',
    'hola',
    'gracias',
    'por favor',
    'como',
    'cómo',
    'estas',
    'estás',
    'que',
    'qué',
    'puedes',
    'ayuda',
    'buenos',
    'buenas',
    'dias',
    'día',
    'tarde',
    'noche',
  ];

  const hits = spanishHints.filter((hint) => normalized.includes(hint)).length;
  if (hits >= 1) return 'es';

  const spanishWordRegex = /\b(hola|gracias|como|estas|que|puedes|ayuda|buenos|buenas|dias|tarde|noche|adios|hasta|luego)\b/;
  if (spanishWordRegex.test(normalized)) return 'es';

  return 'en';
};

const hasMojibake = (text: string): boolean => {
  return /[ÃÂâ€â€™â€œâ€┐≤≥ßφΘⁿ·]/.test(text);
};

const getOrCreateClientId = (): string => {
  const key = 'ai-assistant.client-id';
  const existing = localStorage.getItem(key);
  if (existing) {
    return existing;
  }

  const created = `client-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(key, created);
  return created;
};

const PREFERENCES_CACHE_KEY = 'ai-assistant.preferences-cache';

const getCachedPreferences = (): LocalPreferencesCache => {
  try {
    const raw = localStorage.getItem(PREFERENCES_CACHE_KEY);
    if (!raw) {
      return {};
    }
    return JSON.parse(raw) as LocalPreferencesCache;
  } catch {
    return {};
  }
};

const cachePreferences = (updates: LocalPreferencesCache): void => {
  try {
    const current = getCachedPreferences();
    const merged: LocalPreferencesCache = {
      ...current,
      ...updates,
    };
    localStorage.setItem(PREFERENCES_CACHE_KEY, JSON.stringify(merged));
  } catch {
    // Ignore localStorage failures
  }
};

export const App: React.FC = () => {
  const cachedPreferences = getCachedPreferences();
  const [state, setState] = useState<AppState>({
    sessionId: `session-${Date.now()}`,
    messages: [],
    isLoading: false,
    isPlaying: false,
    audioStartTime: 0,
    volume: 0.7,  // Default volume 70%
    preferredSpriteId: cachedPreferences.default_avatar,
  });

  const [isLoadingAvatar, setIsLoadingAvatar] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const audioRef = useRef<HTMLAudioElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [clientId] = useState<string>(getOrCreateClientId());

  const applySpriteSelection = async (spriteName: string) => {
    if (!spriteName) return;

    try {
      const spriteData = await api.setActiveSprite(spriteName);
      cachePreferences({ default_avatar: spriteName });
      setState((prev) => ({
        ...prev,
        preferredSpriteId: spriteName,
        currentAnimation: spriteData?.avatar ?? prev.currentAnimation,
      }));
    } catch (err) {
      console.warn(`Failed to activate sprite '${spriteName}':`, err);
      cachePreferences({ default_avatar: spriteName });
      setState((prev) => ({
        ...prev,
        preferredSpriteId: spriteName,
      }));
    }
  };

  // Connect to WebSocket event stream on mount
  useEffect(() => {
    wsRef.current = api.connectToEventStream((data) => {
      console.log('Event received:', data);
      // Event stream is primarily for diagnostics/debugging
      // Main chat response contains all needed data
    });

    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Load user preferences on mount (including default avatar/sprite)
  useEffect(() => {
    const loadPreferences = async () => {
      setIsLoadingAvatar(true);
      const cached = getCachedPreferences();
      try {
        const prefs = await api.getPreferences(clientId);
        const avatarToLoad = prefs.preferences?.default_avatar || cached.default_avatar;

        cachePreferences({
          default_avatar: avatarToLoad,
        });

        setState((prev) => ({
          ...prev,
          preferredSpriteId: avatarToLoad || prev.preferredSpriteId,
        }));

        if (avatarToLoad) {
          await applySpriteSelection(avatarToLoad);
        } else {
          // No saved preference, load first available sprite
          await loadFirstAvailableSprite();
        }
      } catch (err) {
        console.warn('Failed to load preferences:', err);

        setState((prev) => ({
          ...prev,
          preferredSpriteId: cached.default_avatar || prev.preferredSpriteId,
        }));

        if (cached.default_avatar) {
          await applySpriteSelection(cached.default_avatar).catch(() => {
            // Continue without avatar if cached sprite fails
          });
        } else {
          // Continue without saved preferences
          await loadFirstAvailableSprite().catch(() => {
            // If all else fails, continue without an avatar
          });
        }
      } finally {
        setIsLoadingAvatar(false);
      }
    };

    const loadFirstAvailableSprite = async () => {
      try {
        const spritesData = await api.getAvailableSprites();
        if (spritesData.sprites && spritesData.sprites.length > 0) {
          const maxSprite = spritesData.sprites.find((sprite: { name: string }) => sprite.name === 'max');
          const spriteToApply = maxSprite?.name || spritesData.sprites[0].name;

          await applySpriteSelection(spriteToApply);

          if (spriteToApply === 'max') {
            await api.updatePreferences({
              client_id: clientId,
              default_avatar: 'max',
            }).catch((error) => {
              console.warn('Failed to persist max as default avatar:', error);
            });
          }
        }
      } catch (err) {
        console.warn('Failed to load first available sprite:', err);
      }
    };

    loadPreferences();
  }, [clientId]);

  // Handle volume changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = state.volume;
    }
  }, [state.volume]);

  // Handle audio playback
  useEffect(() => {
    if (!audioRef.current) return;

    const audio = audioRef.current;
    let mounted = true;

    if (state.audioUrl && state.isPlaying) {
      audio.src = state.audioUrl;
      
      // Wait for metadata to load so we have actual duration
      const handleLoadedMetadata = () => {
        console.log('[App] Audio metadata loaded, actual duration:', audio.duration);
        if (mounted) {
          setState((prev) => ({
            ...prev,
            audioDurationSeconds: audio.duration, // Use actual duration from audio element
          }));
        }
        audio.play();
      };

      audio.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
      
      // If metadata is already loaded, use it immediately
      if (audio.readyState >= 1) {
        handleLoadedMetadata();
      }
    } else {
      audio.pause();
    }

    const handleEnded = () => {
      if (mounted) {
        setState((prev) => ({ ...prev, isPlaying: false }));
      }
    };

    const handleTimeUpdate = () => {
      if (audio.currentTime === 0 && mounted) {
        setState((prev) => ({
          ...prev,
          audioStartTime: Date.now(),
        }));
      }
    };

    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handleTimeUpdate);

    return () => {
      mounted = false;
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handleTimeUpdate);
    };
  }, [state.audioUrl, state.isPlaying]);

  const handleSendMessage = async (text: string) => {
    const normalizedInput = text.normalize('NFC');
    const requestLanguage = detectInputLanguage(normalizedInput);

    // Add user message to chat
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      text: normalizedInput,
      timestamp: Date.now(),
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: undefined,
    }));

    try {
      // Send to backend
      const response: ChatResponse = await api.chat({
        session_id: state.sessionId,
        actor: 'user',
        text: normalizedInput,
        language: requestLanguage,
        permissions: ['*'],
        client_id: clientId,
        preferred_sprite: state.preferredSpriteId,
      });

      // Add assistant message to chat
      const assistantMessage: Message = {
        id: `msg-${Date.now()}-1`,
        role: 'assistant',
        text: response.text,
        timestamp: Date.now(),
        tool_results: response.tool_results,
      };

      // Build audio URL
      let audioUrl: string | undefined;
      if (response.audio) {
        const audioPath = response.audio.audio_path ?? response.audio.wav_path;
        if (audioPath) {
          const cacheToken = response.audio.debug?.after?.file_mtime_ns ?? Date.now();
          audioUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${audioPath}?t=${cacheToken}`;
        }
      }

      console.log('[App] Chat response received with audio duration:', response.audio?.duration_seconds);

      // Log animation details
      if (response.avatar?.animation) {
        console.log('[App] Avatar animation received:', {
          audioTimelineMs: response.avatar.animation.audio_duration_ms,
          numFrames: response.avatar.animation.frames.length,
          lastFrame: response.avatar.animation.frames[response.avatar.animation.frames.length - 1],
        });
      }

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        currentAnimation: response.avatar,
        audioUrl,
        isLoading: false,
        isPlaying: !!response.audio,
        audioStartTime: Date.now(),
        audioDurationSeconds: response.audio?.duration_seconds,
        voiceDebug: {
          requestLanguage,
          audioLanguage: response.audio?.language,
          voiceId: response.audio?.voice_id,
          durationSeconds: response.audio?.duration_seconds,
          artifactId: response.audio?.artifact_id,
          wavPath: response.audio?.audio_path ?? response.audio?.wav_path,
          encodingOk: !hasMojibake(response.text),
          glitchRequested: response.audio?.debug?.glitch_requested,
          glitchApplied: response.audio?.debug?.glitch_applied,
          glitchError: response.audio?.debug?.glitch_error,
          glitchEffects: response.audio?.debug?.glitch_effects,
          glitchIntensity: response.audio?.debug?.glitch_intensity,
          fileSizeBefore: response.audio?.debug?.before?.file_size,
          fileSizeAfter: response.audio?.debug?.after?.file_size,
          mtimeBefore: response.audio?.debug?.before?.file_mtime_ns,
          mtimeAfter: response.audio?.debug?.after?.file_mtime_ns,
        },
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
      console.error('Chat error:', error);
    }
  };

  const handlePreferencesApplied = (preferences: {
    sprite?: string;
  }) => {
    cachePreferences({
      default_avatar: preferences.sprite,
    });

    setState((prev) => ({
      ...prev,
      preferredSpriteId: preferences.sprite ?? prev.preferredSpriteId,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !state.isLoading) {
      handleSendMessage(inputValue);
      setInputValue('');
    }
  };

  const toggleAudioPlayback = () => {
    if (state.audioUrl) {
      setState((prev) => ({
        ...prev,
        isPlaying: !prev.isPlaying,
      }));
    }
  };

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <ChatView
              state={state}
              setState={setState}
              toggleAudioPlayback={toggleAudioPlayback}
              audioRef={audioRef}
              isLoadingAvatar={isLoadingAvatar}
              inputValue={inputValue}
              setInputValue={setInputValue}
              handleSubmit={handleSubmit}
            />
          }
        />
        <Route
          path="/settings"
          element={
            <SettingsPage
              clientId={clientId}
              onAvatarApplied={applySpriteSelection}
              onPreferencesApplied={handlePreferencesApplied}
            />
          }
        />
      </Routes>
    </Router>
  );
};

// Chat View Component
const ChatView: React.FC<{
  state: AppState;
  setState: React.Dispatch<React.SetStateAction<AppState>>;
  toggleAudioPlayback: () => void;
  audioRef: React.RefObject<HTMLAudioElement>;
  isLoadingAvatar?: boolean;
  inputValue: string;
  setInputValue: React.Dispatch<React.SetStateAction<string>>;
  handleSubmit: (e: React.FormEvent) => void;
}> = ({
  state,
  setState,
  toggleAudioPlayback,
  audioRef,
  isLoadingAvatar = false,
  inputValue,
  setInputValue,
  handleSubmit,
}) => {
  const [diagnosticsExpanded, setDiagnosticsExpanded] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-top">
          <h1>AI Assistant</h1>
          <div className="header-controls">
            <p className="session-id">Session: {state.sessionId.substring(0, 20)}...</p>
            <a href="/settings" className="btn-settings" title="Settings">
              ⚙️
            </a>
          </div>
        </div>

        {state.voiceDebug && (
          <div className="diagnostics-section">
            <button
              className="diagnostics-toggle"
              onClick={() => setDiagnosticsExpanded(!diagnosticsExpanded)}
              title={diagnosticsExpanded ? 'Hide diagnostics' : 'Show diagnostics'}
            >
              <span className={`chevron ${diagnosticsExpanded ? 'expanded' : ''}`}>▶</span>
              Voice Diagnostics
            </button>
            {diagnosticsExpanded && (
              <div className="voice-debug-panel">
                <div className="voice-debug-grid">
                  <span>Requested Language</span>
                  <span>{state.voiceDebug.requestLanguage}</span>
                  <span>Audio Language</span>
                  <span>{state.voiceDebug.audioLanguage ?? 'n/a'}</span>
                  <span>Voice ID</span>
                  <span>{state.voiceDebug.voiceId ?? 'n/a'}</span>
                  <span>Duration</span>
                  <span>{state.voiceDebug.durationSeconds ? `${state.voiceDebug.durationSeconds.toFixed(2)}s` : 'n/a'}</span>
                  <span>Artifact</span>
                  <span>{state.voiceDebug.artifactId ?? 'n/a'}</span>
                  <span>Glitch Requested</span>
                  <span>{state.voiceDebug.glitchRequested ? 'yes' : 'no'}</span>
                  <span>Glitch Applied</span>
                  <span>{state.voiceDebug.glitchApplied ? 'yes' : 'no'}</span>
                  <span>Glitch Effects</span>
                  <span>{state.voiceDebug.glitchEffects?.join(', ') || 'n/a'}</span>
                  <span>Glitch Intensity</span>
                  <span>{typeof state.voiceDebug.glitchIntensity === 'number' ? state.voiceDebug.glitchIntensity.toFixed(2) : 'n/a'}</span>
                  <span>File Size (B/A)</span>
                  <span>
                    {typeof state.voiceDebug.fileSizeBefore === 'number' && typeof state.voiceDebug.fileSizeAfter === 'number'
                      ? `${state.voiceDebug.fileSizeBefore} → ${state.voiceDebug.fileSizeAfter}`
                      : 'n/a'}
                  </span>
                  <span>Glitch Error</span>
                  <span>{state.voiceDebug.glitchError || 'none'}</span>
                  <span>Encoding Check</span>
                  <span className={state.voiceDebug.encodingOk ? 'encoding-ok' : 'encoding-bad'}>
                    {state.voiceDebug.encodingOk ? 'OK' : 'MOJIBAKE DETECTED'}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </header>

      {state.error && (
        <div className="error-banner">
          <p>{state.error}</p>
          <button onClick={() => setState((prev) => ({ ...prev, error: undefined }))}>
            Dismiss
          </button>
        </div>
      )}

      <div className="main-content">
        <div className="avatar-container">
          <AvatarStage
            animation={state.currentAnimation}
            audioStartTime={state.audioStartTime}
            isPlaying={state.isPlaying}
            isLoadingAvatar={isLoadingAvatar}
            audioRef={audioRef}
            audioDurationSeconds={state.audioDurationSeconds}
          />

          {state.audioUrl && (
            <div className="audio-controls">
              <button
                className={`playback-button ${state.isPlaying ? 'playing' : ''}`}
                onClick={toggleAudioPlayback}
                title={state.isPlaying ? 'Pause' : 'Play'}
              >
                {state.isPlaying ? '⏸' : '▶'}
              </button>
              <span className="audio-indicator">
                {state.isPlaying ? '🔊 Playing...' : '🔇 Ready'}
              </span>
              <div className="volume-control">
                <span className="volume-label">🔊</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round(state.volume * 100)}
                  onChange={(e) => setState((prev) => ({ ...prev, volume: parseInt(e.target.value) / 100 }))}
                  className="volume-slider"
                  title="Volume"
                />
                <span className="volume-value">{Math.round(state.volume * 100)}%</span>
              </div>
            </div>
          )}
        </div>

        <div className="chat-container">
          <ChatPanel
            messages={state.messages}
            isLoading={state.isLoading}
          />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="global-input-bar">
        <span className="input-prompt">&gt;</span>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your message..."
          disabled={state.isLoading}
          className="message-input"
          autoFocus
        />
      </form>

      <audio ref={audioRef} />
    </div>
  );
};
