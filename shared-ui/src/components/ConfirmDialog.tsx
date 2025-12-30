import React from 'react';

interface ConfirmDialogProps {
  /** Dialog title */
  title: string;
  /** Dialog message */
  message: string;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Whether dialog is open */
  isOpen: boolean;
  /** Callback on confirm */
  onConfirm: () => void;
  /** Callback on cancel */
  onCancel: () => void;
  /** Danger mode (red confirm button) */
  danger?: boolean;
}

/**
 * ConfirmDialog component for confirmation prompts.
 */
export function ConfirmDialog({
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isOpen,
  onConfirm,
  onCancel,
  danger = false,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="confirm-dialog-overlay" onClick={onCancel}>
      <div 
        className="confirm-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="confirm-dialog-title">{title}</h3>
        <p className="confirm-dialog-message">{message}</p>
        <div className="confirm-dialog-actions">
          <button 
            className="cancel-btn"
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button 
            className={`confirm-btn ${danger ? 'danger' : ''}`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
      <style>{`
        .confirm-dialog-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .confirm-dialog {
          background: white;
          border-radius: 8px;
          padding: 24px;
          max-width: 400px;
          width: 100%;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }
        .confirm-dialog-title {
          margin: 0 0 8px;
          font-size: 18px;
          font-weight: 600;
        }
        .confirm-dialog-message {
          margin: 0 0 24px;
          color: #6b7280;
        }
        .confirm-dialog-actions {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
        }
        .cancel-btn {
          padding: 8px 16px;
          border: 1px solid #d1d5db;
          background: white;
          border-radius: 6px;
          cursor: pointer;
        }
        .confirm-btn {
          padding: 8px 16px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }
        .confirm-btn.danger {
          background: #dc2626;
        }
      `}</style>
    </div>
  );
}
