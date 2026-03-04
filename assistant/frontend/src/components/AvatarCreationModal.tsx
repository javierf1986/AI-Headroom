import React from 'react';
import { SpriteUploadForm } from './SpriteUploadForm';
import './AvatarCreationModal.css';

interface AvatarCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: (spriteName: string) => void;
  disabled?: boolean;
}

export const AvatarCreationModal: React.FC<AvatarCreationModalProps> = ({
  isOpen,
  onClose,
  onUploadComplete,
  disabled = false,
}) => {
  if (!isOpen) {
    return null;
  }

  const handleUploadComplete = async (spriteName: string) => {
    onUploadComplete(spriteName);
    onClose();
  };

  return (
    <div className="avatar-creation-modal-overlay">
      <div className="avatar-creation-modal">
        <div className="modal-header">
          <h2>Create New Avatar</h2>
          <button
            className="modal-close-btn"
            onClick={onClose}
            disabled={disabled}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="modal-content">
          <SpriteUploadForm
            onUploadComplete={handleUploadComplete}
            disabled={disabled}
          />
        </div>
      </div>
    </div>
  );
};
