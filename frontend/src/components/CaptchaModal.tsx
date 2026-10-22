import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  SunMoon,
  ExternalLink,
  KeyRound
} from 'lucide-react';
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
  const [zoom, setZoom] = useState<number>(1.5); // Default to 1.5x zoom so captcha is big and clear
  const [inverted, setInverted] = useState<boolean>(false);
  const [imageKey, setImageKey] = useState<number>(Date.now());
  const [imgError, setImgError] = useState<boolean>(false);

  const labName =
    lab === 'labB' || lab === 'cityscan'
      ? 'CityScan Imaging'
      : lab === 'labC' || lab === 'vitals'
      ? 'Vitals Laboratory'
      : lab;

  const imageUrl = `${getCaptchaImageUrl(runId, lab)}?t=${imageKey}`;

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

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.5, 3));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.5, 1));
  const handleRefreshImage = () => {
    setImgError(false);
    setImageKey(Date.now());
  };

  return (
    <div className="modal-overlay">
      <div
        className="modal-content"
        style={{
          maxWidth: '560px',
          width: '94%',
          background: 'var(--bg-card)',
          borderRadius: '18px',
          border: '1px solid var(--border-strong)',
          color: 'var(--text-main)',
          boxShadow: 'var(--shadow-lg)'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          background: 'var(--s-wait-bg)',
          borderBottom: '1px solid var(--border-color)',
          borderTopLeftRadius: '18px',
          borderTopRightRadius: '18px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px'
        }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'rgba(122, 63, 0, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <ShieldAlert size={24} color="#B45309" />
          </div>
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--s-wait-text)', margin: 0 }}>
              Human CAPTCHA Challenge
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--s-wait-text)', opacity: 0.9, margin: '2px 0 0' }}>
              Portal: <strong>{labName}</strong>
            </p>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
            The automated agent paused execution for human verification.
            Inspect the high-clarity CAPTCHA challenge below and enter the characters:
          </p>

          {error && (
            <div style={{
              background: 'var(--s-fail-bg)',
              border: '1px solid #FCA5A5',
              color: 'var(--s-fail-text)',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '13.5px'
            }}>
              {error}
            </div>
          )}

          {/* CAPTCHA Toolbar & Display Box */}
          <div style={{
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border-color)',
            borderRadius: '14px',
            padding: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            {/* Toolbar for Zoom & Enhancement */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '8px',
              fontSize: '12px'
            }}>
              <span style={{ fontWeight: 600, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>Challenge Image</span>
                <span style={{ background: 'var(--bg-card)', padding: '1px 6px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                  {zoom}x Zoom
                </span>
              </span>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  className="btn"
                  title="Zoom In"
                  style={{ width: '30px', height: '30px', minHeight: '30px', padding: 0 }}
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleZoomOut}
                  className="btn"
                  title="Zoom Out"
                  style={{ width: '30px', height: '30px', minHeight: '30px', padding: 0 }}
                >
                  <ZoomOut size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setInverted(!inverted)}
                  className="btn"
                  title="Invert Contrast"
                  style={{ width: '30px', height: '30px', minHeight: '30px', padding: 0, background: inverted ? 'var(--primary-light)' : undefined }}
                >
                  <SunMoon size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleRefreshImage}
                  className="btn"
                  title="Refresh Image"
                  style={{ width: '30px', height: '30px', minHeight: '30px', padding: 0 }}
                >
                  <RefreshCw size={14} />
                </button>
                <a
                  href={imageUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  title="Open in new tab"
                  style={{ width: '30px', height: '30px', minHeight: '30px', padding: 0, textDecoration: 'none' }}
                >
                  <ExternalLink size={14} />
                </a>
              </div>
            </div>

            {/* Image Preview Container */}
            <div style={{
              background: '#FFFFFF',
              border: '2px solid var(--border-strong)',
              borderRadius: '10px',
              padding: '24px 16px',
              minHeight: '130px',
              maxHeight: '260px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'auto',
              boxShadow: 'inset 0 1px 4px rgba(0,0,0,0.04)'
            }}>
              {imgError ? (
                <div style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: '13px' }}>
                  <p>Image not loaded.</p>
                  <button type="button" onClick={handleRefreshImage} className="btn" style={{ fontSize: '12px', minHeight: '28px', marginTop: '6px' }}>
                    Retry loading
                  </button>
                </div>
              ) : (
                <img
                  src={imageUrl}
                  alt="CAPTCHA Challenge"
                  onError={() => setImgError(true)}
                  style={{
                    transform: `scale(${zoom})`,
                    transformOrigin: 'center center',
                    filter: inverted ? 'invert(1) hue-rotate(180deg) contrast(1.2)' : 'none',
                    transition: 'transform 0.15s ease',
                    maxWidth: zoom <= 1 ? '100%' : 'none',
                    maxHeight: zoom <= 1 ? '180px' : 'none',
                    objectFit: 'contain',
                    borderRadius: '4px',
                    display: 'block'
                  }}
                />
              )}
            </div>
          </div>

          {/* Answer Form */}
          <form onSubmit={handleSubmitAnswer}>
            <div className="field" style={{ gap: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: 650, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <KeyRound size={15} color="#0B7A75" />
                <span>Enter CAPTCHA Characters</span>
              </label>

              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  placeholder="e.g. YQT85"
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  autoFocus
                  required
                  style={{
                    fontSize: '18px',
                    fontWeight: 700,
                    letterSpacing: '3px',
                    fontFamily: 'var(--font-mono)',
                    textTransform: 'uppercase',
                    textAlign: 'center',
                    padding: '0 16px',
                    minHeight: '48px'
                  }}
                />
                <button
                  type="submit"
                  className="btn primary"
                  disabled={submitting}
                  style={{ minWidth: '120px', minHeight: '48px', fontSize: '15px', fontWeight: 700 }}
                >
                  {submitting ? 'Verifying...' : 'Submit Answer'}
                </button>
              </div>
            </div>
          </form>

          {/* Alternative Solve Option */}
          <div style={{
            borderTop: '1px solid var(--border-color)',
            paddingTop: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '10px'
          }}>
            <span style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
              Or solve directly in browser session:
            </span>
            <button
              type="button"
              onClick={handleSolvedInLiveView}
              className="btn"
              style={{ fontSize: '13px', minHeight: '36px', padding: '0 14px', fontWeight: 600 }}
              disabled={submitting}
            >
              <CheckCircle size={15} color="#0B7A75" />
              <span>I Solved It in Live View</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
