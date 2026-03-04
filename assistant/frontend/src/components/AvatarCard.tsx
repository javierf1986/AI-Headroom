import React, { useState } from 'react';
import { VoiceSelectorSimple } from './VoiceSelectorSimple';
import { api, API_BASE } from '../api';
import './AvatarCard.css';

interface Sprite {
  name: string;
  display_name: string;
  image_path: string;
  frame_width: number;
  frame_height: number;
  frames_per_row: number;
  total_frames: number;
  persona?: string;
  preferred_voice_en: string;
  preferred_voice_es: string;
  glitch_enabled?: boolean;
  glitch_intensity?: number;
  glitch_effects?: string[];
}

interface AvatarCardProps {
  sprite: Sprite;
  isDefault: boolean;
  onSetDefault: (spriteName: string) => void;
  onVoicesChanged: (spriteName: string, voiceEn: string, voiceEs: string) => void;
  onDelete?: (spriteName: string) => void;
  disabled?: boolean;
}

export const AvatarCard: React.FC<AvatarCardProps> = ({
  sprite,
  isDefault,
  onSetDefault,
  onVoicesChanged,
  onDelete,
  disabled = false,
}) => {
  const [voiceEn, setVoiceEn] = useState(sprite.preferred_voice_en);
  const [voiceEs, setVoiceEs] = useState(sprite.preferred_voice_es);
  const [persona, setPersona] = useState(sprite.persona ?? '');
  const [frameWidth, setFrameWidth] = useState(sprite.frame_width);
  const [frameHeight, setFrameHeight] = useState(sprite.frame_height);
  const [framesPerRow, setFramesPerRow] = useState(sprite.frames_per_row);
  const [totalFrames, setTotalFrames] = useState(sprite.total_frames);
  const [glitchEnabled, setGlitchEnabled] = useState(sprite.glitch_enabled ?? false);
  const [glitchIntensity, setGlitchIntensity] = useState(sprite.glitch_intensity ?? 0.5);
  const [glitchEffects, setGlitchEffects] = useState(sprite.glitch_effects ?? []);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleVoiceChange = async (language: 'en' | 'es', newVoice: string) => {
    if (language === 'en') {
      setVoiceEn(newVoice);
    } else {
      setVoiceEs(newVoice);
    }
  };

  const toggleGlitchEffect = (effect: string) => {
    setGlitchEffects((prev) =>
      prev.includes(effect) ? prev.filter((e) => e !== effect) : [...prev, effect]
    );
  };

  const handleSaveAll = async () => {
    try {
      setIsSaving(true);
      await api.updateSprite(sprite.name, {
        preferred_voice_en: voiceEn,
        preferred_voice_es: voiceEs,
        persona,
        frame_width: frameWidth,
        frame_height: frameHeight,
        frames_per_row: framesPerRow,
        total_frames: totalFrames,
        glitch_enabled: glitchEnabled,
        glitch_intensity: glitchIntensity,
        glitch_effects: glitchEffects,
      });
      onVoicesChanged(sprite.name, voiceEn, voiceEs);
    } catch (err) {
      console.error('Failed to save settings:', err);
      // Revert on error
      setVoiceEn(sprite.preferred_voice_en);
      setVoiceEs(sprite.preferred_voice_es);
      setPersona(sprite.persona ?? '');
      setFrameWidth(sprite.frame_width);
      setFrameHeight(sprite.frame_height);
      setFramesPerRow(sprite.frames_per_row);
      setTotalFrames(sprite.total_frames);
      setGlitchEnabled(sprite.glitch_enabled ?? false);
      setGlitchIntensity(sprite.glitch_intensity ?? 0.5);
      setGlitchEffects(sprite.glitch_effects ?? []);
    } finally {
      setIsSaving(false);
    }
  };

  const isDirty =
    voiceEn !== sprite.preferred_voice_en ||
    voiceEs !== sprite.preferred_voice_es ||
    persona !== (sprite.persona ?? '') ||
    frameWidth !== sprite.frame_width ||
    frameHeight !== sprite.frame_height ||
    framesPerRow !== sprite.frames_per_row ||
    totalFrames !== sprite.total_frames ||
    glitchEnabled !== (sprite.glitch_enabled ?? false) ||
    glitchIntensity !== (sprite.glitch_intensity ?? 0.5) ||
    JSON.stringify(glitchEffects) !== JSON.stringify(sprite.glitch_effects ?? []);

  return (
    <div className={`avatar-card ${isDefault ? 'is-default' : ''} ${!isExpanded ? 'collapsed' : ''}`}>
      <div className="avatar-card-header">
        <div className="avatar-card-title">
          <h3>{sprite.display_name}</h3>
          {isDefault && <span className="default-badge">✓ Default</span>}
        </div>
        {sprite.name !== 'retro-character-v1' && (
          <button
            className="avatar-delete-btn"
            onClick={() => setShowDeleteConfirm(true)}
            disabled={disabled}
            title="Delete this avatar"
          >
            ✕
          </button>
        )}
      </div>

      <div className="avatar-preview" onClick={() => setIsExpanded(!isExpanded)} style={{ cursor: 'pointer' }}>
        {isDefault && <div className="preview-checkmark">✓</div>}
        <img
          src={`${API_BASE}${sprite.image_path}`}
          alt={sprite.display_name}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
          title="Avatar preview - Click to expand/collapse"
        />
      </div>

      {isExpanded && <div className="avatar-persona-edit">
        <h4>LLM Personality</h4>
        <textarea
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          disabled={disabled}
          placeholder="Describe this avatar's personality and behavior..."
          className="persona-textarea"
        />
      </div>}

      {isExpanded && <div className="avatar-sprite-config">
        <h4>Sprite Sheet Configuration</h4>
        <div className="sprite-config-grid">
          <label>
            Frame Width
            <input
              type="number"
              value={frameWidth}
              onChange={(e) => setFrameWidth(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={disabled}
              min="1"
            />
          </label>
          <label>
            Frame Height
            <input
              type="number"
              value={frameHeight}
              onChange={(e) => setFrameHeight(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={disabled}
              min="1"
            />
          </label>
          <label>
            Frames per Row
            <input
              type="number"
              value={framesPerRow}
              onChange={(e) => setFramesPerRow(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={disabled}
              min="1"
            />
          </label>
          <label>
            Total Frames
            <input
              type="number"
              value={totalFrames}
              onChange={(e) => setTotalFrames(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={disabled}
              min="1"
            />
          </label>
        </div>
      </div>}

      {isExpanded && <div className="avatar-voices">
        <h4>Voice Preferences</h4>
        <VoiceSelectorSimple
          language="en"
          selectedVoice={voiceEn}
          onSelect={(v) => handleVoiceChange('en', v)}
          disabled={disabled}
        />
        <VoiceSelectorSimple
          language="es"
          selectedVoice={voiceEs}
          onSelect={(v) => handleVoiceChange('es', v)}
          disabled={disabled}
        />
      </div>}

      {isExpanded && <div className="avatar-glitches">
        <h4>Audio Glitch Effects</h4>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={glitchEnabled}
            onChange={(e) => setGlitchEnabled(e.target.checked)}
            disabled={disabled}
          />
          <span>Enable glitches</span>
        </label>

        {glitchEnabled && (
          <div className="glitch-settings">
            <label htmlFor={`intensity-${sprite.name}`}>
              Intensity: {Math.round(glitchIntensity * 100)}%
            </label>
            <input
              id={`intensity-${sprite.name}`}
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={glitchIntensity}
              onChange={(e) => setGlitchIntensity(parseFloat(e.target.value))}
              disabled={disabled}
              className="intensity-slider"
            />

            <label>Effect Types</label>
            <div className="effects-grid">
              {['stutter', 'pitch', 'static', 'volume'].map((effect) => (
                <label key={effect} className="effect-option">
                  <input
                    type="checkbox"
                    checked={glitchEffects.includes(effect)}
                    onChange={() => toggleGlitchEffect(effect)}
                    disabled={disabled}
                  />
                  <span>{effect}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>}

      {isExpanded && <div className="avatar-actions">
        {isDirty && (
          <button
            className="btn-save-settings"
            onClick={handleSaveAll}
            disabled={isSaving || disabled}
          >
            {isSaving ? 'Saving...' : 'Save All Settings'}
          </button>
        )}
        {!isDefault && (
          <button
            className="btn-set-default"
            onClick={() => onSetDefault(sprite.name)}
            disabled={disabled}
          >
            Set as Default
          </button>
        )}
      </div>}

      {isExpanded && showDeleteConfirm && (
        <div className="delete-confirm">
          <p>Delete "{sprite.display_name}"?</p>
          <div className="delete-confirm-actions">
            <button
              className="btn-confirm-delete"
              onClick={async () => {
                try {
                  await api.deleteSprite(sprite.name);
                  onDelete?.(sprite.name);
                } catch (err) {
                  console.error('Failed to delete sprite:', err);
                }
                setShowDeleteConfirm(false);
              }}
            >
              Yes, Delete
            </button>
            <button
              className="btn-cancel-delete"
              onClick={() => setShowDeleteConfirm(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
