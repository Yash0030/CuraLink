import React, { useState } from 'react';
import { X, Plus, Trash2, Globe, Lock, ShieldCheck, Building2 } from 'lucide-react';
import type { LabInfo } from '../types';
import { addCustomLab, deleteCustomLab } from '../api';
import { useConfirm } from './ConfirmModal';

interface ManageLabsModalProps {
  labs: LabInfo[];
  isOpen: boolean;
  onClose: () => void;
  onLabsUpdated: () => Promise<void>;
}

export const ManageLabsModal: React.FC<ManageLabsModalProps> = ({
  labs,
  isOpen,
  onClose,
  onLabsUpdated,
}) => {
  const { confirm, showAlert } = useConfirm();
  const [isAdding, setIsAdding] = useState(false);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddLab = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a lab name');
      return;
    }
    if (!url.trim()) {
      setError('Please provide the lab portal URL');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await addCustomLab({
        name: name.trim(),
        url: url.trim(),
        username: username.trim() || undefined,
        password: password.trim() || undefined,
      });
      setName('');
      setUrl('');
      setUsername('');
      setPassword('');
      setIsAdding(false);
      await onLabsUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to add lab');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (labKey: string, labName: string) => {
    const confirmed = await confirm({
      title: 'Remove Lab Portal',
      message: `Are you sure you want to remove "${labName}"?`,
      confirmText: 'Remove Lab',
      cancelText: 'Cancel',
      isDanger: true,
    });
    if (!confirmed) return;
    try {
      setDeletingKey(labKey);
      await deleteCustomLab(labKey);
      await onLabsUpdated();
    } catch (err: any) {
      await showAlert('Failed to Remove Lab', err.message || 'Failed to delete lab');
    } finally {
      setDeletingKey(null);
    }
  };

  const customLabs = labs.filter(l => l.is_custom);
  const defaultLabs = labs.filter(l => !l.is_custom);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={e => e.stopPropagation()}
        style={{
          maxWidth: '680px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-card)',
          borderRadius: '16px',
          border: '1px solid var(--border-color)',
          color: 'var(--text-main)',
          fontFamily: "'Onest', sans-serif"
        }}
      >
        {/* Header */}
        <div style={{
          padding: '24px 28px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              background: 'var(--primary-light)',
              color: 'var(--primary)',
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Building2 size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>Connected Labs</h2>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: '2px 0 0' }}>
                Configure connected diagnostic lab portals, credentials, and custom URLs.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            type="button"
            className="btn"
            style={{ width: '40px', height: '40px', minHeight: 'unset', padding: 0 }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Area */}
        <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
          {error && (
            <div style={{
              background: '#FEE2E2',
              border: '1px solid #FCA5A5',
              color: '#991B1B',
              padding: '12px 16px',
              borderRadius: '10px',
              fontSize: '13.5px',
              marginBottom: '18px'
            }}>
              {error}
            </div>
          )}

          {/* Action button to add lab */}
          {!isAdding && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <span style={{ fontSize: '14px', color: '#3A4A5E', fontWeight: 500 }}>
                {labs.length} portal{labs.length !== 1 ? 's' : ''} connected
              </span>
              <button
                type="button"
                onClick={() => { setIsAdding(true); setError(null); }}
                className="btn primary"
                style={{ minHeight: '40px', padding: '0 16px', fontSize: '13.5px' }}
              >
                <Plus size={16} />
                <span>Add custom lab</span>
              </button>
            </div>
          )}

          {/* Add Lab Form */}
          {isAdding && (
            <form
              onSubmit={handleAddLab}
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-color)',
                borderRadius: '14px',
                padding: '20px',
                marginBottom: '24px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
                  Connect New Lab Portal
                </h3>
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                <div className="field">
                  <label>Lab Portal Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Apex Diagnostics"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    required
                  />
                </div>

                <div className="field">
                  <label>Portal URL *</label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '18px' }}>
                <div className="field">
                  <label>Default Username (Optional)</label>
                  <input
                    type="text"
                    placeholder="Portal Username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                  />
                </div>

                <div className="field">
                  <label>Default Password (Optional)</label>
                  <input
                    type="password"
                    placeholder="Portal Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  className="btn"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn primary"
                  disabled={loading}
                >
                  {loading ? 'Connecting Lab...' : 'Save Lab Portal'}
                </button>
              </div>
            </form>
          )}

          {/* User Custom Labs */}
          {customLabs.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <div style={{ fontSize: '13px', fontWeight: 650, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px' }}>
                Your Custom Lab Portals ({customLabs.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {customLabs.map(lab => (
                  <div
                    key={lab.key}
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '12px',
                      padding: '16px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 650, fontSize: '15px', color: 'var(--text-main)' }}>{lab.name}</span>
                        <span className="tag" style={{ background: 'var(--primary-light)', color: 'var(--primary-dark)' }}>
                          Custom Lab
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '6px', fontSize: '13px', color: 'var(--text-dim)' }}>
                        {(lab.url || lab.reports_path) && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Globe size={14} color="var(--text-dim)" />
                            <span>{lab.url || lab.reports_path}</span>
                          </div>
                        )}
                        {lab.default_username && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Lock size={14} color="var(--text-dim)" />
                            <span>User: {lab.default_username}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDelete(lab.key, lab.name)}
                      disabled={deletingKey === lab.key}
                      className="btn danger"
                      style={{ minHeight: '36px', padding: '0 12px', fontSize: '13px' }}
                      title="Delete this lab"
                    >
                      <Trash2 size={14} />
                      <span>{deletingKey === lab.key ? 'Deleting...' : 'Delete'}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* System Default Labs */}
          <div>
            <div style={{ fontSize: '13px', fontWeight: 650, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px' }}>
              Built-in System Labs ({defaultLabs.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {defaultLabs.map(lab => (
                <div
                  key={lab.key}
                  style={{
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '12px',
                    padding: '14px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 650, fontSize: '15px', color: 'var(--text-main)' }}>{lab.name}</span>
                      <span className="tag">
                        {lab.layout}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#4A5A6E', marginTop: '4px' }}>
                      Endpoint: {lab.reports_path}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#074F4B', fontWeight: 600 }}>
                    <ShieldCheck size={16} />
                    <span>Built-in</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 28px',
          borderTop: '1px solid #E4EAF0',
          display: 'flex',
          justifyContent: 'flex-end'
        }}>
          <button type="button" onClick={onClose} className="btn">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
