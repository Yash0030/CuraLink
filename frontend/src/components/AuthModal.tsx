import React, { useState } from 'react';
import { X } from 'lucide-react';
import { login, signup } from '../api';
import type { UserProfile } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onSuccess: (user: UserProfile) => void;
  canDismiss?: boolean;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  canDismiss = false,
}) => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'signup') {
        if (!name.trim()) throw new Error('Please enter your full name');
        if (!email.trim() || !password.trim()) throw new Error('Please enter email and password');
        if (password.length < 6) throw new Error('Password must be at least 6 characters');
        const res = await signup({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password,
        });
        onSuccess(res.user);
      } else {
        if (!email.trim() || !password.trim()) throw new Error('Please enter email and password');
        const res = await login({
          email: email.trim().toLowerCase(),
          password,
        });
        onSuccess(res.user);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const isUp = mode === 'signup';

  return (
    <div
      className="modal-overlay"
      style={{
        padding: 0,
        background: canDismiss ? 'rgba(15, 27, 45, 0.65)' : '#F4F6F8',
        alignItems: 'stretch',
        justifyContent: 'stretch'
      }}
      onClick={canDismiss && onClose ? onClose : undefined}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          width: '100%',
          minHeight: '100vh',
          fontFamily: "'Onest', system-ui, sans-serif",
          color: 'var(--text-main)',
          background: 'var(--bg-page)',
          position: 'relative'
        }}
        onClick={e => e.stopPropagation()}
      >
        {canDismiss && onClose && (
          <button
            type="button"
            onClick={onClose}
            className="btn"
            style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              zIndex: 10,
              width: '40px',
              height: '40px',
              padding: 0
            }}
            title="Close"
          >
            <X size={18} />
          </button>
        )}

        {/* Left Hero Section (Deep Forest Teal) */}
        <section style={{
          flex: '1 1 460px',
          boxSizing: 'border-box',
          background: '#08403D',
          color: '#fff',
          padding: 'clamp(32px, 5vw, 72px)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: '48px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0B7A75" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 12h4l3-7 4 14 3-7h4"></path>
              </svg>
            </div>
            <span style={{ fontSize: '16px', fontWeight: 700 }}>Health Record Organizer</span>
          </div>

          <div style={{ maxWidth: '480px' }}>
            <h1 style={{
              margin: 0,
              fontSize: 'clamp(34px, 4.4vw, 52px)',
              lineHeight: 1.08,
              letterSpacing: '-0.02em',
              fontWeight: 700
            }}>
              Every lab report, in one private timeline.
            </h1>
            <p style={{ margin: '20px 0 0', fontSize: '17px', lineHeight: 1.6, color: '#CFE6E4' }}>
              Sign in once. Your assistant collects reports from each lab portal, removes duplicates and checks that every report belongs to the right patient.
            </p>
          </div>

          <p style={{ margin: 0, fontSize: '14px', color: '#CFE6E4', maxWidth: '420px', lineHeight: 1.5 }}>
            Records are kept separate for each account. Other users never see yours.
          </p>
        </section>

        {/* Right Form Section */}
        <section style={{
          flex: '1 1 460px',
          boxSizing: 'border-box',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '32px 20px',
          background: 'var(--bg-page)'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '420px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 10px 30px rgba(15, 27, 45, 0.05)'
          }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)' }}>
              <button
                type="button"
                className={`tab ${!isUp ? 'on' : ''}`}
                onClick={() => { setMode('login'); setError(null); }}
              >
                Sign in
              </button>
              <button
                type="button"
                className={`tab ${isUp ? 'on' : ''}`}
                onClick={() => { setMode('signup'); setError(null); }}
              >
                Create account
              </button>
            </div>

            <form
              onSubmit={handleSubmit}
              style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '18px' }}
              autoComplete="off"
            >
              {/* Hidden anti-autofill decoy inputs */}
              <input type="text" name="fake_user" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />
              <input type="password" name="fake_pass" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />

              <div>
                <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 700, color: 'var(--text-main)' }}>
                  {isUp ? 'Create your account' : 'Welcome back'}
                </h2>
                <p style={{ margin: '6px 0 0', fontSize: '14.5px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
                  {isUp ? 'Start your own private health record library.' : 'Sign in to see your records and collection runs.'}
                </p>
              </div>

              {error && (
                <div style={{
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

              {isUp && (
                <label className="field">
                  Full name
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Full name"
                    autoComplete="off"
                    data-lpignore="true"
                    required={isUp}
                  />
                </label>
              )}

              <label className="field">
                Email address
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  autoComplete="off"
                  data-lpignore="true"
                  required
                />
              </label>

              <label className="field">
                Password
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete="new-password"
                  data-lpignore="true"
                  required
                />
              </label>

              <button
                type="submit"
                className="btn primary"
                disabled={loading}
                style={{ marginTop: '4px', minHeight: '48px' }}
              >
                {loading ? 'Processing...' : isUp ? 'Create account' : 'Sign in'}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
};
