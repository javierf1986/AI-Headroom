import React, { useState, useEffect, useRef } from 'react';
import { api, API_BASE } from '../api';

interface Sprite {
  name: string;
  display_name: string;
  image_path: string;
  frame_width: number;
  frame_height: number;
  frames_per_row: number;
  total_frames: number;
  persona?: string;
  glitch_enabled?: boolean;
  glitch_intensity?: number;
  glitch_effects?: string[];
}

interface EditFormState {
  display_name: string;
  frame_width: number;
  frame_height: number;
  frames_per_row: number;
  total_frames: number;
  persona: string;
  glitch_enabled: boolean;
  glitch_intensity: number;
  glitch_effects: string[];
}

interface SpriteSelectorProps {
  selectedSprite: string | null;
  onSelect: (spriteName: string) => void;
  disabled?: boolean;
  onSpritesChanged?: () => void;
}

const BUILTIN = 'retro-character-v1';

export const SpriteSelector: React.FC<SpriteSelectorProps> = ({
  selectedSprite,
  onSelect,
  disabled = false,
  onSpritesChanged,
}) => {
  const [sprites, setSprites] = useState<Sprite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingSprite, setEditingSprite] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [confirmDeleteSprite, setConfirmDeleteSprite] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const statusTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { loadSprites(); }, []);

  const showStatus = (type: 'success' | 'error', text: string) => {
    if (statusTimer.current) clearTimeout(statusTimer.current);
    setStatusMsg({ type, text });
    statusTimer.current = setTimeout(() => setStatusMsg(null), 3500);
  };

  const loadSprites = async () => {
    try {
      setLoading(true);
      const data = await api.getAvailableSprites();
      setSprites(data.sprites || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load sprites:', err);
      setError('Failed to load available sprites');
      setSprites([]);
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (sprite: Sprite) => {
    setEditingSprite(sprite.name);
    setEditForm({
      display_name: sprite.display_name,
      frame_width: sprite.frame_width,
      frame_height: sprite.frame_height,
      frames_per_row: sprite.frames_per_row,
      total_frames: sprite.total_frames,
      persona: sprite.persona || '',
      glitch_enabled: sprite.glitch_enabled || false,
      glitch_intensity: sprite.glitch_intensity || 0.5,
      glitch_effects: sprite.glitch_effects || [],
    });
    setEditError(null);
    setConfirmDeleteSprite(null);
  };

  const cancelEdit = () => {
    setEditingSprite(null);
    setEditForm(null);
    setEditError(null);
  };

  const saveEdit = async () => {
    if (!editingSprite || !editForm) return;
    try {
      setEditSaving(true);
      setEditError(null);
      await api.updateSprite(editingSprite, editForm);
      await loadSprites();
      onSpritesChanged?.();
      cancelEdit();
      showStatus('success', 'Avatar updated successfully.');
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setEditSaving(false);
    }
  };

  const requestDelete = (spriteName: string) => {
    setConfirmDeleteSprite(spriteName);
    setEditingSprite(null);
    setEditForm(null);
  };

  const confirmDelete = async () => {
    if (!confirmDeleteSprite) return;
    try {
      setDeleting(true);
      await api.deleteSprite(confirmDeleteSprite);
      if (selectedSprite === confirmDeleteSprite) onSelect(BUILTIN);
      setConfirmDeleteSprite(null);
      await loadSprites();
      onSpritesChanged?.();
      showStatus('success', 'Avatar deleted.');
    } catch (err) {
      showStatus('error', err instanceof Error ? err.message : 'Failed to delete sprite');
      setConfirmDeleteSprite(null);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <div className="sprite-selector">Loading sprites...</div>;

  if (error) {
    return (
      <div className="sprite-selector error">
        <p>{error}</p>
        <button onClick={loadSprites}>Retry</button>
      </div>
    );
  }

  if (sprites.length === 0) {
    return <div className="sprite-selector">No sprites available</div>;
  }

  return (
    <div className="sprite-selector">
      {statusMsg && (
        <div className={`sprite-status-msg ${statusMsg.type}`}>{statusMsg.text}</div>
      )}

      {confirmDeleteSprite && (
        <div className="sprite-delete-confirm">
          <p>
            Delete <strong>{sprites.find((s) => s.name === confirmDeleteSprite)?.display_name ?? confirmDeleteSprite}</strong>?
            {' '}This cannot be undone.
          </p>
          <div className="sprite-confirm-actions">
            <button className="btn-danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Yes, Delete'}
            </button>
            <button className="btn-secondary" onClick={() => setConfirmDeleteSprite(null)} disabled={deleting}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="sprite-grid">
        {sprites.map((sprite) => {
          const isSelected = selectedSprite === sprite.name;
          const isEditing = editingSprite === sprite.name;
          const isBuiltin = sprite.name === BUILTIN;

          return (
            <div
              key={sprite.name}
              className={`sprite-card ${isSelected ? 'selected' : ''} ${isEditing ? 'editing' : ''}`}
            >
              {isEditing && editForm ? (
                <div className="sprite-edit-form">
                  <h4>Edit Avatar</h4>

                  <label>Display Name</label>
                  <input
                    type="text"
                    value={editForm.display_name}
                    onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                    disabled={editSaving}
                  />

                  <label>Persona / Personality</label>
                  <textarea
                    value={editForm.persona}
                    onChange={(e) => setEditForm({ ...editForm, persona: e.target.value })}
                    disabled={editSaving}
                    placeholder="Define this avatar's personality (e.g., 'You are cheerful and informal')..."
                    rows={3}
                    style={{ resize: 'vertical', minHeight: '60px' }}
                  />

                  <div style={{ marginTop: '16px', padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <label style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={editForm.glitch_enabled}
                        onChange={(e) => setEditForm({ ...editForm, glitch_enabled: e.target.checked })}
                        disabled={editSaving}
                        style={{ marginRight: '8px' }}
                      />
                      <span style={{ fontWeight: '600' }}>Enable Audio Glitches (Max Headroom style)</span>
                    </label>
                    
                    {editForm.glitch_enabled && (
                      <>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.9em' }}>
                          Glitch Intensity: {Math.round(editForm.glitch_intensity * 100)}%
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={editForm.glitch_intensity}
                          onChange={(e) => setEditForm({ ...editForm, glitch_intensity: parseFloat(e.target.value) })}
                          disabled={editSaving}
                          style={{ width: '100%', marginBottom: '12px' }}
                        />
                        
                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9em', fontWeight: '500' }}>
                          Effect Types:
                        </label>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {['stutter', 'pitch', 'static', 'volume'].map(effect => (
                            <label key={effect} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', padding: '4px 8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '4px' }}>
                              <input
                                type="checkbox"
                                checked={editForm.glitch_effects.includes(effect)}
                                onChange={(e) => {
                                  const effects = e.target.checked
                                    ? [...editForm.glitch_effects, effect]
                                    : editForm.glitch_effects.filter(f => f !== effect);
                                  setEditForm({ ...editForm, glitch_effects: effects });
                                }}
                                disabled={editSaving}
                                style={{ marginRight: '6px' }}
                              />
                              <span style={{ textTransform: 'capitalize', fontSize: '0.9em' }}>{effect}</span>
                            </label>
                          ))}
                        </div>
                      </>
                    )}
                  </div>

                  <div className="form-row">
                    <div className="form-col">
                      <label>Frames / Row</label>
                      <input
                        type="number" min={1} max={16}
                        value={editForm.frames_per_row}
                        onChange={(e) => setEditForm({ ...editForm, frames_per_row: parseInt(e.target.value) || 1 })}
                        disabled={editSaving}
                      />
                    </div>
                    <div className="form-col">
                      <label>Total Frames</label>
                      <input
                        type="number" min={1} max={256}
                        value={editForm.total_frames}
                        onChange={(e) => setEditForm({ ...editForm, total_frames: parseInt(e.target.value) || 1 })}
                        disabled={editSaving}
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-col">
                      <label>Frame W (px)</label>
                      <input
                        type="number" min={16} max={512}
                        value={editForm.frame_width}
                        onChange={(e) => setEditForm({ ...editForm, frame_width: parseInt(e.target.value) || 64 })}
                        disabled={editSaving}
                      />
                    </div>
                    <div className="form-col">
                      <label>Frame H (px)</label>
                      <input
                        type="number" min={16} max={512}
                        value={editForm.frame_height}
                        onChange={(e) => setEditForm({ ...editForm, frame_height: parseInt(e.target.value) || 64 })}
                        disabled={editSaving}
                      />
                    </div>
                  </div>

                  {editError && <p className="edit-error">{editError}</p>}

                  <div className="sprite-edit-actions">
                    <button className="btn-primary" onClick={saveEdit} disabled={editSaving}>
                      {editSaving ? 'Saving…' : 'Save'}
                    </button>
                    <button className="btn-secondary" onClick={cancelEdit} disabled={editSaving}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div
                    className="sprite-card-body"
                    onClick={() => !disabled && onSelect(sprite.name)}
                    role="button"
                    tabIndex={disabled ? -1 : 0}
                    onKeyDown={(e) => {
                      if (!disabled && (e.key === 'Enter' || e.key === ' ')) onSelect(sprite.name);
                    }}
                  >
                    <div className="sprite-preview">
                      <img
                        src={(() => {
                          const base = sprite.image_path.startsWith('/') ? `${API_BASE}${sprite.image_path}` : sprite.image_path;
                          const vKey = `${sprite.frame_width}x${sprite.frame_height}_${sprite.total_frames}`;
                          return `${base}?v=${encodeURIComponent(vKey)}`;
                        })()}
                        alt={sprite.display_name}
                        title={sprite.display_name}
                      />
                    </div>
                    <div className="sprite-info">
                      <h4>{sprite.display_name}</h4>
                      <p className="sprite-meta">
                        {sprite.total_frames} frames • {sprite.frame_width}×{sprite.frame_height}px
                      </p>
                    </div>
                    {isSelected && <div className="sprite-badge">✓ Selected</div>}
                  </div>

                  <div className="sprite-card-actions">
                    <button
                      className="btn-icon"
                      title="Edit"
                      onClick={() => startEdit(sprite)}
                      disabled={disabled}
                    >
                      ✏️
                    </button>
                    <button
                      className="btn-icon btn-icon-danger"
                      title={isBuiltin ? 'Cannot delete the default sprite' : 'Delete'}
                      onClick={() => !isBuiltin && requestDelete(sprite.name)}
                      disabled={disabled || isBuiltin}
                    >
                      🗑️
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
