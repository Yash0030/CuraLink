import React, { useState } from 'react';
import { ShieldAlert, CheckCircle } from 'lucide-react';
import { getCaptchaImageUrl, submitCaptchaResolution } from '../api';

interface CaptchaModalProps {
  runId: string;
  lab: string;
  onResolved: () => void;
}

export const CaptchaModal: React.FC<CaptchaModalProps> = ({ runId, lab, onResolved }) => {
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const labName = lab === 'labB' ? 'CityScan Imaging' : lab === 'labC' ? 'Vitals Diagnostics' : lab;
  const imageUrl = getCaptchaImageUrl(runId, lab);

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await submitCaptchaResolution(runId, lab, { answer: answer.trim() });
      setAnswer('');
      onResolved();
    } catch (err: any) {
      setError(err.message || 'Failed to submit CAPTCHA answer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSolvedInLiveView = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await submitCaptchaResolution(runId, lab, { solved_live: true });
      onResolved();
    } catch (err: any) {
      setError(err.message || 'Failed to signal live view solve');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '480px' }}>
        <div style={{
          padding: '16px 20px',
          background: 'rgba(245, 158, 11, 0.12)',
          borderBottom: '1px solid rgba(245, 158, 11, 0.25)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <ShieldAlert size={22} color="#f59e0b" />
          <div>
            <h3 style={{ fontSize: '16px', color: '#fbbf24', margin: 0 }}>Human CAPTCHA Challenge</h3>
            <p style={{ fontSize: '12px', color: '#fef3c7', margin: 0 }}>
              Portal: <strong>{labName}</strong>
            </p>
          </div>
        </div>

        <div style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            The automated agent paused execution. In accordance with zero-bypass safety guidelines,
            please solve the challenge below:
          </p>

          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              marginBottom: '14px'
            }}>
              {error}
            </div>
          )}

          {/* CAPTCHA Image display */}
          <div style={{
            background: '#090d16',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '16px',
            textAlign: 'center',
            marginBottom: '18px'
          }}>
            <img
              src={imageUrl}
              alt="CAPTCHA Challenge"
              style={{ maxHeight: '90px', maxWidth: '100%', objectFit: 'contain', borderRadius: '4px' }}
              onError={(e) => {
                // If direct image fails to render, show notice
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>

          <form onSubmit={handleSubmitAnswer}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Type CAPTCHA Text
            </label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. 4892"
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                autoFocus
                required
              />
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Relaying...' : 'Submit'}
              </button>
            </div>
          </form>

          <div style={{
            borderTop: '1px solid var(--border-color)',
            paddingTop: '14px',
            marginTop: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
              Or solve directly in browser session:
            </span>
            <button
              type="button"
              onClick={handleSolvedInLiveView}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '6px 12px' }}
              disabled={submitting}
            >
              <CheckCircle size={14} color="#10b981" />
              <span>I Solved It in Live View</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
