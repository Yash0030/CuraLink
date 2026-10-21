import React, { useEffect, useState } from 'react';
import { History, ArrowRight, Activity } from 'lucide-react';
import type { RunSummary } from '../types';
import { fetchAllRuns } from '../api';

interface PastRunsViewProps {
  onSelectRun: (runId: string) => void;
}

export const PastRunsView: React.FC<PastRunsViewProps> = ({ onSelectRun }) => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '28px 24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px' }}>Past Collection Runs</h1>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Audit trail of all previous health record extraction and aggregation sessions.
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <Activity size={28} color="#6366f1" style={{ animation: 'spin 1.5s linear infinite', margin: '0 auto 12px' }} />
          <p>Loading runs history...</p>
        </div>
      ) : runs.length === 0 ? (
        <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-dim)' }}>
          <History size={40} style={{ margin: '0 auto 16px', opacity: 0.4 }} />
          <h3 style={{ fontSize: '16px', color: '#fff', marginBottom: '6px' }}>No Past Runs Found</h3>
          <p style={{ fontSize: '13px' }}>Click "New Collection" to initiate an automated agent run.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {runs.map(r => (
            <div
              key={r.id}
              className="glass-panel"
              style={{
                padding: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px',
                transition: 'transform 0.15s ease'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                  <h3 style={{ fontSize: '17px', color: '#fff', margin: 0 }}>{r.patient_name}</h3>
                  <span className={`badge badge-${r.status}`}>
                    {r.status.replace(/_/g, ' ')}
                  </span>
                </div>

                <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <span>Patient ID: <strong>{r.patient_id || 'N/A'}</strong></span>
                  <span>Range: <strong>{r.date_from}</strong> to <strong>{r.date_to}</strong></span>
                  <span>Labs: <strong>{r.labs.join(', ')}</strong></span>
                  <span>Started: {new Date(r.created_at).toLocaleString()}</span>
                </div>
              </div>

              <button
                onClick={() => onSelectRun(r.id)}
                className="btn btn-secondary"
                style={{ padding: '8px 16px' }}
              >
                <span>View Details</span>
                <ArrowRight size={15} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
