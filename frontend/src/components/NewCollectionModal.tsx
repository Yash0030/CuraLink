import React, { useState } from 'react';
import { X } from 'lucide-react';
import type { LabInfo, LabLoginCredential } from '../types';

interface NewCollectionModalProps {
  labs: LabInfo[];
  isOpen: boolean;
  onClose: () => void;
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
  onClose,
  onSubmit,
}) => {
  const [patientName, setPatientName] = useState('Aarav Roy');
  const [patientId, setPatientId] = useState('pt001');
  const [dateFrom, setDateFrom] = useState('2026-01-01');
  const [dateTo, setDateTo] = useState('2026-01-31');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [logins, setLogins] = useState<Record<string, LabLoginCredential>>({
    labA: { enabled: true, username: 'pt001', password: 'demo123' },
    labB: { enabled: true, username: 'pt001', password: 'demo123' },
    labC: { enabled: true, username: 'pt001', password: 'demo123' },
  });

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

  const labDetailsMap: Record<string, { desc: string; badge: string }> = {
    labA: { desc: 'A1 Diagnostics (Table layout)', badge: 'Table' },
    labB: { desc: 'CityScan Imaging (Cards layout + CAPTCHA)', badge: 'Cards' },
    labC: { desc: 'Vitals Diagnostics (Paginated layout + CAPTCHA)', badge: 'Paginated' },
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '640px' }}>
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.02)'
        }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Start New Record Collection</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Orchestrates parallel agents across lab portals with automated deduplication & verification.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '24px' }}>
          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              marginBottom: '18px'
            }}>
              {error}
            </div>
          )}

          {/* Patient Details */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '18px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#cbd5e1' }}>
                Patient Full Name *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="input-field"
                  value={patientName}
                  onChange={e => setPatientName(e.target.value)}
                  placeholder="e.g. Aarav Roy"
                  required
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#cbd5e1' }}>
                Patient ID / MRN (Optional)
              </label>
              <input
                type="text"
                className="input-field"
                value={patientId}
                onChange={e => setPatientId(e.target.value)}
                placeholder="e.g. pt001"
              />
            </div>
          </div>

          {/* Date Range */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '22px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#cbd5e1' }}>
                Date From *
              </label>
              <input
                type="date"
                className="input-field"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#cbd5e1' }}>
                Date To *
              </label>
              <input
                type="date"
                className="input-field"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Lab Portals Section */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#e2e8f0', marginBottom: '10px' }}>
              Select Portals & Credentials (Stored strictly in memory during run)
            </label>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {labs.map(lab => {
                const cred = logins[lab.key] || { enabled: true, username: 'pt001', password: 'demo123' };
                const extra = labDetailsMap[lab.key] || { desc: lab.name, badge: lab.layout };

                return (
                  <div
                    key={lab.key}
                    style={{
                      background: cred.enabled ? 'rgba(30, 41, 59, 0.5)' : 'rgba(15, 23, 42, 0.3)',
                      border: cred.enabled ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: cred.enabled ? '10px' : 0 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={cred.enabled}
                          onChange={() => handleToggleLab(lab.key)}
                          style={{ width: '16px', height: '16px', accentColor: '#6366f1' }}
                        />
                        <span style={{ fontWeight: 600, fontSize: '14px', color: '#fff' }}>{lab.name}</span>
                        <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px', color: '#94a3b8' }}>
                          {extra.badge}
                        </span>
                        {lab.has_captcha && (
                          <span style={{ fontSize: '11px', background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', padding: '2px 6px', borderRadius: '4px' }}>
                            Mock CAPTCHA
                          </span>
                        )}
                      </label>
                    </div>

                    {cred.enabled && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '8px', paddingLeft: '26px' }}>
                        <input
                          type="text"
                          className="input-field"
                          placeholder="Username"
                          value={cred.username}
                          onChange={e => handleUpdateCred(lab.key, 'username', e.target.value)}
                          style={{ padding: '6px 10px', fontSize: '13px' }}
                          required
                        />
                        <input
                          type="password"
                          className="input-field"
                          placeholder="Password"
                          value={cred.password}
                          onChange={e => handleUpdateCred(lab.key, 'password', e.target.value)}
                          style={{ padding: '6px 10px', fontSize: '13px' }}
                          required
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" onClick={onClose} className="btn btn-secondary" disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Launching Agents...' : 'Start Collection Run'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
