import React, { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';
import type { EventLogItem } from '../types';

interface LiveLogProps {
  events: EventLogItem[];
  runStatus: string;
}

export const LiveLog: React.FC<LiveLogProps> = ({ events, runStatus }) => {
  const streamEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} color="#818cf8" />
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Live Agent Audit Log</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {runStatus !== 'completed' && runStatus !== 'failed' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#10b981' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
              <span>Polling every 1.5s</span>
            </div>
          )}
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            {events.length} event{events.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="log-stream">
        {events.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', padding: '12px 0' }}>
            No agent activity recorded yet. Waiting for run initialization...
          </div>
        ) : (
          events.map(ev => {
            const time = new Date(ev.created_at).toLocaleTimeString();
            let msgClass = 'log-msg-info';
            if (ev.level === 'WARNING') msgClass = 'log-msg-warning';
            if (ev.level === 'ERROR') msgClass = 'log-msg-error';

            return (
              <div key={ev.id} className="log-entry">
                <span className="log-time">[{time}]</span>
                <span className="log-agent">{ev.agent}:</span>
                <span className={msgClass}>{ev.message}</span>
              </div>
            );
          })
        )}
        <div ref={streamEndRef} />
      </div>
    </div>
  );
};
