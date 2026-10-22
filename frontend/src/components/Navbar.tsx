import React from 'react';
import { Activity, Plus, Clock, FileText, Building2, LogOut, LogIn } from 'lucide-react';
import type { UserProfile } from '../types';

interface NavbarProps {
  activeTab: 'current' | 'history' | 'timeline';
  onTabChange: (tab: 'current' | 'history' | 'timeline') => void;
  onOpenNewCollection: () => void;
  onOpenManageLabs: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  currentUser: UserProfile | null;
  hasActiveRun: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  onOpenNewCollection,
  onOpenManageLabs,
  onOpenAuth,
  onLogout,
  currentUser,
  hasActiveRun
}) => {
  const initial = currentUser?.name ? currentUser.name.charAt(0).toUpperCase() : 'U';

  return (
    <aside style={{
      width: '260px',
      minWidth: '240px',
      boxSizing: 'border-box',
      background: 'var(--bg-card)',
      borderRight: '1px solid var(--border-color)',
      padding: '28px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      transition: 'background-color 0.2s ease, border-color 0.2s ease'
    }}>
      {/* Brand Logo & Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '12px',
          background: 'var(--primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          boxShadow: '0 2px 8px rgba(11, 122, 117, 0.25)'
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 12h4l3-7 4 14 3-7h4"></path>
          </svg>
        </div>
        <div style={{ fontSize: '15px', fontWeight: 700, lineHeight: 1.2, color: 'var(--text-main)' }}>
          Health Record<br />Organizer
        </div>
      </div>

      {/* New Collection CTA */}
      <button
        type="button"
        onClick={onOpenNewCollection}
        className="btn primary"
        style={{ width: '100%', justifyContent: 'center', fontWeight: 700 }}
      >
        <Plus size={18} strokeWidth={2.4} />
        <span>New collection</span>
      </button>

      {/* Navigation List */}
      <nav aria-label="Main" style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
        <button
          type="button"
          onClick={() => onTabChange('current')}
          className={`nav ${activeTab === 'current' ? 'on' : ''}`}
        >
          <Activity size={19} strokeWidth={1.8} />
          <span style={{ flex: 1, textAlign: 'left' }}>Active run</span>
          {hasActiveRun && (
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)' }} />
          )}
        </button>

        <button
          type="button"
          onClick={() => onTabChange('timeline')}
          className={`nav ${activeTab === 'timeline' ? 'on' : ''}`}
        >
          <FileText size={19} strokeWidth={1.8} />
          <span style={{ flex: 1, textAlign: 'left' }}>Health timeline</span>
        </button>

        <button
          type="button"
          onClick={() => onTabChange('history')}
          className={`nav ${activeTab === 'history' ? 'on' : ''}`}
        >
          <Clock size={19} strokeWidth={1.8} />
          <span style={{ flex: 1, textAlign: 'left' }}>Past runs</span>
        </button>

        <button
          type="button"
          onClick={onOpenManageLabs}
          className="nav"
        >
          <Building2 size={19} strokeWidth={1.8} />
          <span style={{ flex: 1, textAlign: 'left' }}>Labs</span>
        </button>
      </nav>

      {/* User Profile Footer */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        paddingTop: '16px',
        borderTop: '1px solid var(--border-color)'
      }}>
        {currentUser ? (
          <>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'var(--chip-cs-bg)',
              color: 'var(--chip-cs-text)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '14px',
              flexShrink: 0
            }}>
              {initial}
            </div>

            <div style={{ flex: 1, minWidth: 0, lineHeight: 1.3 }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {currentUser.name}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {currentUser.email}
              </div>
            </div>

            <button
              type="button"
              onClick={onLogout}
              className="btn"
              style={{ width: '38px', height: '38px', minHeight: '38px', padding: 0 }}
              title="Sign out"
            >
              <LogOut size={16} strokeWidth={1.8} />
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={onOpenAuth}
            className="btn primary"
            style={{ width: '100%', minHeight: '40px', fontSize: '13.5px' }}
          >
            <LogIn size={15} />
            <span>Sign in</span>
          </button>
        )}
      </div>
    </aside>
  );
};
