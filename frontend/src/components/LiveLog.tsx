import React, { useEffect, useRef, useState } from 'react';
import { Terminal, ArrowDown, Pause, Play } from 'lucide-react';
import type { EventLogItem } from '../types';

interface LiveLogProps {
  events: EventLogItem[];
  runStatus: string;
}

export const LiveLog: React.FC<LiveLogProps> = ({ events, runStatus }) => {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);

  // Scroll only the inner container to bottom when autoScroll is enabled
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Handle user manual scrolling: pause auto-scroll if user scrolled up
  const handleContainerScroll = () => {
    const el = logContainerRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 40;
    if (isAtBottom !== autoScroll) {
      setAutoScroll(isAtBottom);
    }
  };

  const scrollToBottom = () => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
    setAutoScroll(true);
  };

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} color="#818cf8" />
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Live Agent Audit Log</h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Auto-scroll toggle / status */}
          <button
            type="button"
            onClick={() => {
              if (!autoScroll) {
                scrollToBottom();
              } else {
                setAutoScroll(false);
              }
            }}
            title={autoScroll ? 'Auto-scroll is active. Click to pause.' : 'Auto-scroll is paused. Click to resume.'}
            style={{
              background: autoScroll ? 'rgba(99, 102, 241, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              border: autoScroll ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)',
              color: autoScroll ? '#a5b4fc' : '#fbbf24',
              borderRadius: '6px',
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {autoScroll ? <Pause size={12} /> : <Play size={12} />}
            <span>{autoScroll ? 'Auto-scroll ON' : 'Paused (Scrolled up)'}</span>
          </button>

          {!autoScroll && (
            <button
              type="button"
              onClick={scrollToBottom}
              className="btn btn-secondary"
              style={{ padding: '3px 8px', fontSize: '11px', gap: '4px' }}
            >
              <ArrowDown size={12} />
              <span>Jump to latest</span>
            </button>
          )}

          {runStatus !== 'completed' && runStatus !== 'failed' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#10b981' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
              <span>Polling 1.5s</span>
            </div>
          )}

          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            {events.length} event{events.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div
        ref={logContainerRef}
        onScroll={handleContainerScroll}
        className="log-stream"
        style={{ overscrollBehavior: 'contain' }}
      >
        {events.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontStyle: 'italic', padding: '12px 0' }}>
            No agent activity recorded yet. Waiting for run initialization...
          </div>
        ) : (
          events.map(ev => {
            const time = new Date(ev.created_at).toLocaleTimeString();
            const isUser = ev.agent === 'User' || ev.agent === 'User Action' || ev.agent === 'Human';
            let msgClass = 'log-msg-info';
            if (ev.level === 'WARNING') msgClass = 'log-msg-warning';
            if (ev.level === 'ERROR') msgClass = 'log-msg-error';

            return (
              <div key={ev.id} className="log-entry" style={{ display: 'flex', gap: '8px', alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span className="log-time">[{time}]</span>
                <span style={{
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 650,
                  background: isUser ? 'rgba(20, 184, 166, 0.18)' : 'rgba(99, 102, 241, 0.16)',
                  color: isUser ? '#2dd4bf' : '#a5b4fc',
                  border: isUser ? '1px solid rgba(20, 184, 166, 0.4)' : '1px solid rgba(99, 102, 241, 0.35)'
                }}>
                  {isUser ? '👤 Human (You)' : `🤖 Agent: ${ev.agent}`}
                </span>
                <span className={msgClass}>{ev.message}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

