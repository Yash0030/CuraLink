import React from 'react';
import { ShieldAlert, UserCheck } from 'lucide-react';

export const Banner: React.FC = () => {
  return (
    <div style={{
      background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(20, 184, 166, 0.15) 100%)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      padding: '8px 24px',
      fontSize: '13px',
      color: '#e2e8f0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '24px',
      flexWrap: 'wrap'
    }}>
      <div style={{ display: 'flex', alignContent: 'center', alignItems: 'center', gap: '8px' }}>
        <ShieldAlert size={16} color="#38bdf8" />
        <span><strong>Notice:</strong> This application operates strictly on <strong>synthetic data only</strong>. No real protected health information (PHI) is processed.</span>
      </div>
      <div style={{ display: 'flex', alignContent: 'center', alignItems: 'center', gap: '8px' }}>
        <UserCheck size={16} color="#34d399" />
        <span><strong>Human-in-the-Loop Safety:</strong> All CAPTCHAs are resolved exclusively by a human. Zero automated bypass.</span>
      </div>
    </div>
  );
};
