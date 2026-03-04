import React, { useState } from 'react';
import { api } from '../api';

interface SpriteUploadFormProps {
  onUploadComplete?: (spriteName: string) => void;
  disabled?: boolean;
}

export const SpriteUploadForm: React.FC<SpriteUploadFormProps> = ({
  onUploadComplete,
  disabled = false,
}) => {
  const [formData, setFormData] = useState({
    sprite_name: '',
    display_name: '',
    frame_width: 64,
    frame_height: 64,
    frames_per_row: 1,
    total_frames: 1,
    persona: '',
    glitch_enabled: false,
    glitch_intensity: 0.5,
    glitch_effects: [] as string[],
  });
  const [file, setFile] = useState<File | null>(null);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Auto-calculate frame dimensions based on image size and grid layout
  const recalculateFrameDimensions = (
    width: number,
    height: number,
    framesPerRow: number,
    totalFrames: number
  ) => {
    if (!width || !height || !framesPerRow || !totalFrames) return;

    const rows = Math.ceil(totalFrames / framesPerRow);
    const frameWidth = Math.floor(width / framesPerRow);
    const frameHeight = Math.floor(height / rows);

    setFormData((prev) => ({
      ...prev,
      frame_width: Math.max(16, frameWidth),
      frame_height: Math.max(16, frameHeight),
    }));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    const numericFields = ['frame_width', 'frame_height', 'frames_per_row', 'total_frames', 'glitch_intensity'];
    const nextValue =
      e.target instanceof HTMLInputElement && e.target.type === 'checkbox'
        ? e.target.checked
        : numericFields.includes(name)
          ? (name === 'glitch_intensity' ? parseFloat(value) : parseInt(value, 10))
          : value;
    const newData = {
      ...formData,
      [name]: nextValue,
    };
    setFormData(newData);

    // When user changes grid parameters, auto-recalculate frame dimensions
    if (imageDimensions && (name === 'frames_per_row' || name === 'total_frames')) {
      const framesPerRow = name === 'frames_per_row' ? parseInt(value) : newData.frames_per_row;
      const totalFrames = name === 'total_frames' ? parseInt(value) : newData.total_frames;
      recalculateFrameDimensions(imageDimensions.width, imageDimensions.height, framesPerRow, totalFrames);
    }
  };

  const toggleGlitchEffect = (effect: string) => {
    setFormData((prev) => ({
      ...prev,
      glitch_effects: prev.glitch_effects.includes(effect)
        ? prev.glitch_effects.filter((existing) => existing !== effect)
        : [...prev.glitch_effects, effect],
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.type.startsWith('image/png')) {
        setMessage({ type: 'error', text: 'Please select a PNG file' });
        setFile(null);
        return;
      }
      if (selectedFile.size > 10 * 1024 * 1024) {
        setMessage({ type: 'error', text: 'File size must be less than 10MB' });
        setFile(null);
        return;
      }

      // Read image dimensions
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          const dims = { width: img.width, height: img.height };
          setImageDimensions(dims);
          setMessage({
            type: 'success',
            text: `Image loaded: ${img.width}x${img.height}px. Adjust frames per row/total to auto-calculate frame dimensions.`,
          });
          // Auto-calculate frame dimensions based on current grid settings
          recalculateFrameDimensions(
            img.width,
            img.height,
            formData.frames_per_row,
            formData.total_frames
          );
        };
        img.onerror = () => {
          setMessage({ type: 'error', text: 'Failed to read image dimensions' });
          setFile(null);
        };
        img.src = event.target?.result as string;
      };
      reader.readAsDataURL(selectedFile);

      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setMessage({ type: 'error', text: 'Please select a PNG file' });
      return;
    }

    if (!formData.sprite_name || !formData.display_name) {
      setMessage({ type: 'error', text: 'Please fill in sprite name and display name' });
      return;
    }

    try {
      setUploading(true);
      const uploadFormData = new FormData();
      uploadFormData.append('sprite_name', formData.sprite_name);
      uploadFormData.append('display_name', formData.display_name);
      uploadFormData.append('file', file);
      uploadFormData.append('frame_width', formData.frame_width.toString());
      uploadFormData.append('frame_height', formData.frame_height.toString());
      uploadFormData.append('frames_per_row', formData.frames_per_row.toString());
      uploadFormData.append('total_frames', formData.total_frames.toString());
      uploadFormData.append('persona', formData.persona);
      uploadFormData.append('glitch_enabled', formData.glitch_enabled.toString());
      uploadFormData.append('glitch_intensity', formData.glitch_intensity.toString());
      formData.glitch_effects.forEach((effect) => uploadFormData.append('glitch_effects', effect));

      await api.uploadSprite(uploadFormData);

      setMessage({ type: 'success', text: `Sprite "${formData.display_name}" uploaded successfully!` });
      setFormData({
        sprite_name: '',
        display_name: '',
        frame_width: 64,
        frame_height: 64,
        frames_per_row: 1,
        total_frames: 1,
        persona: '',
        glitch_enabled: false,
        glitch_intensity: 0.5,
        glitch_effects: [],
      });
      setFile(null);
      setImageDimensions(null);

      if (onUploadComplete) {
        onUploadComplete(formData.sprite_name);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setMessage({ type: 'error', text: `Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}` });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="sprite-upload-form">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="sprite_name">Sprite Name *</label>
          <input
            id="sprite_name"
            type="text"
            name="sprite_name"
            value={formData.sprite_name}
            onChange={handleInputChange}
            placeholder="e.g., my-custom-sprite"
            disabled={uploading || disabled}
            required
          />
          <small>Unique identifier (lowercase, hyphens ok)</small>
        </div>

        <div className="form-group">
          <label htmlFor="display_name">Display Name *</label>
          <input
            id="display_name"
            type="text"
            name="display_name"
            value={formData.display_name}
            onChange={handleInputChange}
            placeholder="e.g., My Custom Character"
            disabled={uploading || disabled}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="persona">Persona / Personality</label>
          <textarea
            id="persona"
            name="persona"
            value={formData.persona}
            onChange={handleInputChange}
            placeholder="Define this avatar's personality (e.g., 'You are cheerful and informal')..."
            disabled={uploading || disabled}
            rows={3}
          />
          <small>This persona guides how the LLM responds when this avatar is active.</small>
        </div>

        <div className="form-group">
          <label htmlFor="file">PNG File *</label>
          <input
            id="file"
            type="file"
            accept="image/png"
            onChange={handleFileChange}
            disabled={uploading || disabled}
            required
          />
          {file && <small>Selected: {file.name}</small>}
        </div>

        <fieldset disabled={uploading || disabled} className="form-group">
          <legend>Sprite Sheet Grid</legend>
          {imageDimensions && (
            <small style={{ display: 'block', marginBottom: '8px' }}>
              Image: {imageDimensions.width}×{imageDimensions.height}px —
              frame size auto-calculated from grid layout
            </small>
          )}
          <div className="form-row">
            <div className="form-col">
              <label htmlFor="frames_per_row">Frames Per Row</label>
              <input
                id="frames_per_row"
                type="number"
                name="frames_per_row"
                value={formData.frames_per_row}
                onChange={handleInputChange}
                min="1"
                max="16"
              />
            </div>
            <div className="form-col">
              <label htmlFor="total_frames">Total Frames</label>
              <input
                id="total_frames"
                type="number"
                name="total_frames"
                value={formData.total_frames}
                onChange={handleInputChange}
                min="1"
                max="256"
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-col">
              <label htmlFor="frame_width">
                Frame Width (px){imageDimensions ? ' — auto' : ''}
              </label>
              <input
                id="frame_width"
                type="number"
                name="frame_width"
                value={formData.frame_width}
                onChange={handleInputChange}
                min="16"
                max="512"
                readOnly={!!imageDimensions}
                style={imageDimensions ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
              />
            </div>
            <div className="form-col">
              <label htmlFor="frame_height">
                Frame Height (px){imageDimensions ? ' — auto' : ''}
              </label>
              <input
                id="frame_height"
                type="number"
                name="frame_height"
                value={formData.frame_height}
                onChange={handleInputChange}
                min="16"
                max="512"
                readOnly={!!imageDimensions}
                style={imageDimensions ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
              />
            </div>
          </div>
        </fieldset>

        <fieldset disabled={uploading || disabled} className="form-group glitch-settings">
          <legend>Audio Glitch Effects (Max Headroom style)</legend>

          <label className="checkbox-label" htmlFor="glitch_enabled">
            <input
              id="glitch_enabled"
              type="checkbox"
              name="glitch_enabled"
              checked={formData.glitch_enabled}
              onChange={handleInputChange}
            />
            <span>Enable audio glitches for this avatar</span>
          </label>

          {formData.glitch_enabled && (
            <>
              <label htmlFor="glitch_intensity">
                Glitch Intensity: {Math.round(formData.glitch_intensity * 100)}%
              </label>
              <input
                id="glitch_intensity"
                type="range"
                name="glitch_intensity"
                min="0"
                max="1"
                step="0.05"
                value={formData.glitch_intensity}
                onChange={handleInputChange}
              />

              <label>Effect Types</label>
              <div className="effects-grid">
                {['stutter', 'pitch', 'static', 'volume'].map((effect) => (
                  <label key={effect} className="effect-option">
                    <input
                      type="checkbox"
                      checked={formData.glitch_effects.includes(effect)}
                      onChange={() => toggleGlitchEffect(effect)}
                    />
                    <span>{effect}</span>
                  </label>
                ))}
              </div>
            </>
          )}
        </fieldset>

        {message && (
          <div className={`message ${message.type}`}>
            {message.text}
          </div>
        )}

        <button
          type="submit"
          disabled={uploading || disabled || !file}
          className="btn-primary"
        >
          {uploading ? 'Uploading...' : 'Upload Sprite'}
        </button>
      </form>
    </div>
  );
};
