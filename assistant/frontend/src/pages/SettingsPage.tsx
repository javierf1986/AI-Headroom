import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AvatarGrid } from '../components/AvatarGrid';
import { AvatarCreationModal } from '../components/AvatarCreationModal';
import { api } from '../api';
import './SettingsPage.css';

interface SettingsPageProps {
  clientId: string;
  onAvatarApplied?: (spriteName: string) => Promise<void> | void;
  onPreferencesApplied?: (preferences: {
    sprite?: string;
  }) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  clientId,
  onAvatarApplied,
  onPreferencesApplied,
}) => {
  const navigate = useNavigate();
  const [defaultAvatar, setDefaultAvatar] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, [clientId]);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const data = await api.getPreferences(clientId);
      setDefaultAvatar(data.preferences?.default_avatar || '');
      setMessage(null);
    } catch (err) {
      console.error('Failed to load preferences:', err);
      setMessage({ type: 'error', text: 'Failed to load preferences' });
    } finally {
      setLoading(false);
    }
  };

  const handleDefaultAvatarChanged = async (spriteName: string) => {
    try {
      setSaving(true);
      await api.updatePreferences({
        client_id: clientId,
        default_avatar: spriteName || undefined,
      });

      setDefaultAvatar(spriteName);

      if (spriteName) {
        await onAvatarApplied?.(spriteName);
      }

      onPreferencesApplied?.({
        sprite: spriteName || undefined,
      });

      setMessage({ type: 'success', text: `Default avatar set to "${spriteName}"` });
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      console.error('Failed to save preferences:', err);
      setMessage({ type: 'error', text: 'Failed to save default avatar' });
    } finally {
      setSaving(false);
    }
  };

  const handleUploadComplete = async (spriteName: string) => {
    try {
      // Set the newly uploaded sprite as the default
      await handleDefaultAvatarChanged(spriteName);
      setMessage({ type: 'success', text: 'Avatar created and set as default!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      console.error('Failed to set uploaded avatar as default:', err);
      setMessage({ type: 'error', text: 'Avatar uploaded, but failed to set as default' });
    }
  };

  if (loading) {
    return <div className="settings-page"><p>Loading preferences...</p></div>;
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
        <button className="btn-back" onClick={() => navigate('/')}>
          ← Back to Chat
        </button>
      </div>

      <div className="settings-content">
        <section className="settings-section">
          <div className="section-header">
            <h2>Avatar Configuration</h2>
            <button
              className="btn-add-avatar"
              onClick={() => setIsModalOpen(true)}
              disabled={saving}
            >
              + Add Avatar
            </button>
          </div>
          <p>Manage your avatars and set the default one for conversations. Each avatar has its own voice preferences.</p>
          <AvatarGrid
            key={`grid-${defaultAvatar || 'none'}`}
            defaultAvatar={defaultAvatar}
            onDefaultAvatarChanged={handleDefaultAvatarChanged}
            disabled={saving}
          />
        </section>

        {message && (
          <div className={`settings-message ${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="settings-actions">
          <button
            className="btn-secondary"
            onClick={() => navigate('/')}
          >
            Done
          </button>
        </div>
      </div>

      <AvatarCreationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onUploadComplete={handleUploadComplete}
        disabled={saving}
      />
    </div>
  );
};
