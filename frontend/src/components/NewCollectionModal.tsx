import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { LabInfo, LabLoginCredential, UserProfile } from '../types';

interface NewCollectionModalProps {
  labs: LabInfo[];
  isOpen: boolean;
  currentUser?: UserProfile | null;
  onClose: () => void;
  onOpenManageLabs?: () => void;
  onSubmit: (data: {
    patient_name: string;
    patient_id?: string;
    date_from: string;
    date_to: string;
    logins: Record<string, LabLoginCredential>;
  }) => Promise<void>;
}

export const NewCollectionModal: React.FC<NewCollectionModalProps> = ({
  labs,
  isOpen,
  currentUser,
  onClose,
  onOpenManageLabs,
  onSubmit,
}) => {
  const [patientName, setPatientName] = useState('');
  const [patientId, setPatientId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [logins, setLogins] = useState<Record<string, LabLoginCredential>>({});

  useEffect(() => {
    setLogins(prev => {
      const next: Record<string, LabLoginCredential> = { ...prev };
      labs.forEach(lab => {
        if (!next[lab.key]) {
          next[lab.key] = {
            enabled: true,
            username: lab.default_username || '',
            password: lab.default_password || '',
          };
        }
      });
      return next;
    });
  }, [labs]);

  useEffect(() => {
    if (isOpen && currentUser?.name && !patientName) {
      setPatientName(currentUser.name);
    }
  }, [isOpen, currentUser]);

  if (!isOpen) return null;

  const handleToggleLab = (key: string) => {
    setLogins(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        enabled: !prev[key]?.enabled
      }
    }));
  };

  const handleUpdateCred = (key: string, field: 'username' | 'password', val: string) => {
    setLogins(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: val
      }
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientName.trim()) {
      setError('Patient Name is required');
      return;
    }
    if (!dateFrom || !dateTo) {
      setError('Please select both From and To dates');
      return;
    }
    const hasEnabledLab = Object.values(logins).some(l => l.enabled);
    if (!hasEnabledLab) {
      setError('Please select at least one lab portal');
      return;
    }

    setError(null);
    setLoading(true);
    try {
      await onSubmit({
        patient_name: patientName.trim(),
        patient_id: patientId.trim() || undefined,
        date_from: dateFrom,
        date_to: dateTo,
        logins
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to start collection run');
    } finally {
      setLoading(false);
    }
  };

  const labTagMap: Record<string, string> = {
    labA: 'Table',
    labB: 'Cards',
    labC: 'Paginated',
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form
        role="dialog"
        aria-labelledby="dlg"
        onSubmit={handleSubmit}
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '680px',
          boxSizing: 'border-box',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '18px',
          boxShadow: '0 24px 64px rgba(15, 27, 45, 0.35)',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
        autoComplete="off"
      >
        {/* Anti-autofill decoy inputs */}
        <input type="text" name="decoy_user" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />
        <input type="password" name="decoy_pass" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />

        {/* Dialog Header */}
        <header style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          padding: '28px 32px 20px'
        }}>
          <div>
            <h1 id="dlg" style={{ margin: 0, fontSize: '24px', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>
              Start a new collection
            </h1>
            <p style={{ margin: '6px 0 0', fontSize: '14.5px', lineHeight: 1.5, color: 'var(--text-muted)', maxWidth: '460px' }}>
              Your assistant signs in to each lab you pick, downloads matching reports and checks them before adding them to the timeline.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn"
            style={{ width: '44px', minHeight: '44px', padding: 0 }}
            aria-label="Close"
          >
            <X size={18} strokeWidth={2} />
          </button>
        </header>

        {error && (
          <div style={{
            margin: '0 32px 16px',
            background: '#FEE2E2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '10px 14px',
            borderRadius: '10px',
            fontSize: '13.5px'
          }}>
            {error}
          </div>
        )}

        {/* Form Body */}
        <div style={{ padding: '0 32px 8px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Patient Fieldset */}
          <fieldset style={{ border: 0, margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <legend style={{ fontSize: '15px', fontWeight: 700, padding: 0, marginBottom: '12px', color: 'var(--text-main)' }}>
              Patient
            </legend>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
              <label className="field">
                <span className="field-label">
                  <span>Full name</span>
                </span>
                <input
                  type="text"
                  placeholder="Patient full name"
                  value={patientName}
                  onChange={e => setPatientName(e.target.value)}
                  autoComplete="off"
                  data-lpignore="true"
                  required
                />
              </label>
              <label className="field">
                <span className="field-label">
                  <span>Patient ID or MRN</span>
                  <span className="hint">Optional</span>
                </span>
                <input
                  type="text"
                  placeholder="Patient ID or MRN"
                  value={patientId}
                  onChange={e => setPatientId(e.target.value)}
                  autoComplete="off"
                  data-lpignore="true"
                />
              </label>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
              <label className="field">
                <span className="field-label">
                  <span>From</span>
                </span>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span className="field-label">
                  <span>To</span>
                </span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  required
                />
              </label>
            </div>
          </fieldset>

          {/* Labs to search Fieldset */}
          <fieldset style={{ border: 0, margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '12px', marginBottom: '4px' }}>
              <legend style={{ fontSize: '15px', fontWeight: 700, padding: 0, color: 'var(--text-main)' }}>
                Labs to search
              </legend>
              {onOpenManageLabs && (
                <button
                  type="button"
                  onClick={onOpenManageLabs}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '14px',
                    fontWeight: 600,
                    color: 'var(--primary)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  Add or manage labs
                </button>
              )}
            </div>
            <p style={{ margin: '0 0 4px', fontSize: '13.5px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              Sign-in details are only used for this run and stay inside your account.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {labs.map(lab => {
                const cred = logins[lab.key] || {
                  enabled: true,
                  username: lab.default_username || '',
                  password: lab.default_password || ''
                };
                const tagLabel = labTagMap[lab.key] || (lab.is_custom ? 'Custom' : lab.layout);

                return (
                  <div key={lab.key} className="lab">
                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px' }}>
                      <label className="chk">
                        <input
                          type="checkbox"
                          checked={cred.enabled}
                          onChange={() => handleToggleLab(lab.key)}
                        />
                        {lab.name}
                      </label>
                      <span className="tag">{tagLabel}</span>
                      {lab.has_captcha && <span className="tag cap">CAPTCHA</span>}
                    </div>

                    {cred.enabled && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                        <label className="field">
                          <span className="field-label">
                            <span>Portal username</span>
                          </span>
                          <input
                            type="text"
                            placeholder="Portal username"
                            value={cred.username}
                            onChange={e => handleUpdateCred(lab.key, 'username', e.target.value)}
                            autoComplete="off"
                            data-lpignore="true"
                            required
                          />
                        </label>
                        <label className="field">
                          <span className="field-label">
                            <span>Portal password</span>
                          </span>
                          <input
                            type="password"
                            placeholder="Portal password"
                            value={cred.password}
                            onChange={e => handleUpdateCred(lab.key, 'password', e.target.value)}
                            autoComplete="new-password"
                            data-lpignore="true"
                            required
                          />
                        </label>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </fieldset>
        </div>

        {/* Dialog Footer */}
        <footer style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'flex-end',
          gap: '12px',
          padding: '20px 32px 28px',
          borderTop: '1px solid var(--border-color)',
          marginTop: '16px'
        }}>
          <button type="button" onClick={onClose} className="btn" disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn primary" disabled={loading}>
            {loading ? 'Starting collection...' : 'Start collection'}
          </button>
        </footer>
      </form>
    </div>
  );
};
