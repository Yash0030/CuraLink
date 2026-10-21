import React from 'react';
import { Activity, Plus, Clock, FileText } from 'lucide-react';

interface NavbarProps {
  activeTab: 'current' | 'history' | 'timeline';
  onTabChange: (tab: 'current' | 'history' | 'timeline') => void;
  onOpenNewCollection: () => void;
  hasActiveRun: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  onOpenNewCollection,
  hasActiveRun
}) => {
  return (
    <nav style={{
      borderBottom: '1px solid var(--border-color)',
      background: 'rgba(9, 13, 22, 0.9)',
      backdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '0 24px',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          background: 'linear-gradient(135deg, #6366f1 0%, #14b8a6 100%)',
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
        }}>
          <Activity size={20} color="#fff" />
        </div>
        <div>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '17px', color: '#fff' }}>
            Personal Health Record Organizer
          </span>
          <span style={{
            fontSize: '11px',
            background: 'rgba(99, 102, 241, 0.2)',
            color: '#a5b4fc',
            padding: '2px 8px',
            borderRadius: '9999px',
            marginLeft: '10px',
            fontWeight: 600,
            letterSpacing: '0.04em'
          }}>
            ZIRO HACKATHON 2026
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => onTabChange('current')}
          style={{
            background: activeTab === 'current' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            border: 'none',
            color: activeTab === 'current' ? '#fff' : 'var(--text-muted)',
            padding: '8px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <Activity size={16} />
          <span>Active Run</span>
          {hasActiveRun && (
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
          )}
        </button>

        <button
          onClick={() => onTabChange('timeline')}
          style={{
            background: activeTab === 'timeline' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            border: 'none',
            color: activeTab === 'timeline' ? '#fff' : 'var(--text-muted)',
            padding: '8px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <FileText size={16} />
          <span>Health Timeline</span>
        </button>

        <button
          onClick={() => onTabChange('history')}
          style={{
            background: activeTab === 'history' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            border: 'none',
            color: activeTab === 'history' ? '#fff' : 'var(--text-muted)',
            padding: '8px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
        >
          <Clock size={16} />
          <span>Past Runs</span>
        </button>

        <button
          onClick={onOpenNewCollection}
          className="btn btn-primary"
          style={{ marginLeft: '12px' }}
        >
          <Plus size={16} />
          <span>New Collection</span>
        </button>
      </div>
    </nav>
  );
};
