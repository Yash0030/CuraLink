import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';

export interface ConfirmDialogOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDanger?: boolean;
  type?: 'confirm' | 'alert' | 'danger';
}

interface ConfirmContextType {
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
  showAlert: (title: string, message: string) => Promise<void>;
}

const ConfirmContext = createContext<ConfirmContextType | undefined>(undefined);

export const ConfirmProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [dialogState, setDialogState] = useState<{
    isOpen: boolean;
    options: ConfirmDialogOptions;
    resolve: (val: boolean) => void;
  } | null>(null);

  const confirm = useCallback((options: ConfirmDialogOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setDialogState({
        isOpen: true,
        options,
        resolve,
      });
    });
  }, []);

  const showAlert = useCallback((title: string, message: string): Promise<void> => {
    return new Promise((resolve) => {
      setDialogState({
        isOpen: true,
        options: {
          title,
          message,
          confirmText: 'OK',
          type: 'alert',
        },
        resolve: () => resolve(),
      });
    });
  }, []);

  const handleClose = (result: boolean) => {
    if (dialogState) {
      dialogState.resolve(result);
      setDialogState(null);
    }
  };

  return (
    <ConfirmContext.Provider value={{ confirm, showAlert }}>
      {children}
      {dialogState && dialogState.isOpen && (
        <div
          className="modal-overlay"
          onClick={() => handleClose(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.72)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px'
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '460px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              boxShadow: 'var(--shadow-lg)',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              animation: 'scaleIn 0.15s ease-out',
              color: 'var(--text-main)'
            }}
          >
            {/* Header with Icon */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '12px',
                  background: dialogState.options.isDanger || dialogState.options.type === 'danger'
                    ? 'rgba(239, 68, 68, 0.14)'
                    : 'rgba(20, 184, 166, 0.14)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                {dialogState.options.isDanger || dialogState.options.type === 'danger' ? (
                  <AlertTriangle size={22} color="#EF4444" />
                ) : (
                  <Info size={22} color="var(--primary)" />
                )}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <h3 style={{ margin: '0 0 6px', fontSize: '18px', fontWeight: 700, color: 'var(--text-main)' }}>
                  {dialogState.options.title}
                </h3>
                <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.5, color: 'var(--text-muted)', whiteSpace: 'pre-line' }}>
                  {dialogState.options.message}
                </p>
              </div>

              <button
                type="button"
                onClick={() => handleClose(false)}
                className="btn"
                style={{ width: '32px', height: '32px', minHeight: '32px', padding: 0, borderRadius: '8px', color: 'var(--text-dim)' }}
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {/* Actions Footer */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
              {dialogState.options.type !== 'alert' && (
                <button
                  type="button"
                  onClick={() => handleClose(false)}
                  className="btn"
                  style={{ minHeight: '38px', padding: '0 16px', fontSize: '14px', fontWeight: 600 }}
                >
                  {dialogState.options.cancelText || 'Cancel'}
                </button>
              )}

              <button
                type="button"
                onClick={() => handleClose(true)}
                className={`btn ${dialogState.options.isDanger || dialogState.options.type === 'danger' ? 'danger' : 'primary'}`}
                style={{ minHeight: '38px', padding: '0 18px', fontSize: '14px', fontWeight: 650 }}
                autoFocus
              >
                {dialogState.options.confirmText || (dialogState.options.isDanger ? 'Delete' : 'Confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
};

export const useConfirm = () => {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error('useConfirm must be used within a ConfirmProvider');
  }
  return context;
};
