import React, { useState, useEffect } from 'react';
import { AvatarCard } from './AvatarCard';
import { api } from '../api';
import './AvatarGrid.css';

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

interface AvatarGridProps {
  defaultAvatar: string | null;
  onDefaultAvatarChanged: (spriteName: string) => void;
  disabled?: boolean;
}

export const AvatarGrid: React.FC<AvatarGridProps> = ({
  defaultAvatar,
  onDefaultAvatarChanged,
  disabled = false,
}) => {
  const [sprites, setSprites] = useState<Sprite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSprites();
  }, []);

  const loadSprites = async () => {
    try {
      setLoading(true);
      const data = await api.getAvailableSprites();
      setSprites(data.sprites || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load sprites:', err);
      setError('Failed to load avatars');
      setSprites([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = (spriteName: string) => {
    onDefaultAvatarChanged(spriteName);
  };

  const handleVoicesChanged = (spriteName: string, voiceEn: string, voiceEs: string) => {
    // Update local state to reflect the saved changes
    setSprites((prev) =>
      prev.map((s) =>
        s.name === spriteName
          ? { ...s, preferred_voice_en: voiceEn, preferred_voice_es: voiceEs }
          : s
      )
    );
  };

  const handleDelete = (spriteName: string) => {
    setSprites((prev) => prev.filter((s) => s.name !== spriteName));
    // If deleted sprite was the default, clear the default selection
    if (defaultAvatar === spriteName) {
      onDefaultAvatarChanged('');
    }
  };

  if (loading) {
    return <div className="avatar-grid loading">Loading avatars...</div>;
  }

  if (error) {
    return <div className="avatar-grid error">{error}</div>;
  }

  if (sprites.length === 0) {
    return <div className="avatar-grid empty">No avatars available.</div>;
  }

  return (
    <div className="avatar-grid">
      {sprites.map((sprite) => (
        <AvatarCard
          key={sprite.name}
          sprite={sprite}
          isDefault={defaultAvatar === sprite.name}
          onSetDefault={handleSetDefault}
          onVoicesChanged={handleVoicesChanged}
          onDelete={handleDelete}
          disabled={disabled}
        />
      ))}
    </div>
  );
};
