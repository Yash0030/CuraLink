import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Copy,
  Ban,
  XCircle,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  FileCheck2
} from 'lucide-react';
import type { RunDetailsResponse, CandidateItem, EventLogItem } from '../types';
import {
  fetchRunDetails,
  fetchRunEvents,
  fetchRunCandidates,
  submitApproval,
  getPdfFileUrl
} from '../api';
import { LiveLog } from './LiveLog';
import { ApprovalPanel } from './ApprovalPanel';
import { CaptchaModal } from './CaptchaModal';

interface RunViewProps {
  runId: string;
  onRunCompleted: () => void;
}

export const RunView: React.FC<RunViewProps> = ({ runId, onRunCompleted }) => {
  const [details, setDetails] = useState<RunDetailsResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [events, setEvents] = useState<EventLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);

  // Poll run details and events every 1.5 seconds as specified
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const [det, cand, evs] = await Promise.all([
          fetchRunDetails(runId),
          fetchRunCandidates(runId),
          fetchRunEvents(runId, 0)
        ]);

        if (isMounted) {
          setDetails(det);
          setCandidates(cand);
          setEvents(evs);
          setLoading(false);

          if (det.run.status === 'completed') {
            onRunCompleted();
          }
        }
      } catch (err: any) {
        if (isMounted) setPollError(err.message || 'Failed to poll run data');
      }
    };

    loadData();
    const timer = setInterval(loadData, 1500);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [runId]);

  const handleApprove = async (approved: boolean, overrides: Record<string, string>) => {
    setApproving(true);
    try {
      await submitApproval(runId, approved, overrides);
      // Immediately reload details
      const [det, cand, evs] = await Promise.all([
        fetchRunDetails(runId),
        fetchRunCandidates(runId),
        fetchRunEvents(runId, 0)
      ]);
      setDetails(det);
      setCandidates(cand);
      setEvents(evs);
    } catch (err: any) {
      alert(err.message || 'Failed to submit approval');
    } finally {
      setApproving(false);
    }
  };

  if (loading && !details) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
        <Activity size={32} color="#6366f1" style={{ animation: 'spin 1.5s linear infinite', margin: '0 auto 16px' }} />
        <p>Connecting to run orchestrator {runId}...</p>
      </div>
    );
  }

  if (!details) {
    return <div style={{ padding: '40px', color: '#f87171' }}>Run not found or failed to load.</div>;
  }

  const run = details.run;
  const counts = details.decision_counts;
  const isWaitingApproval = run.status === 'waiting_approval';
  const isCompleted = run.status === 'completed';
  const waitingCaptchaLab = details.waiting_captchas?.[0];

  return (
    <div style={{ maxWidth: '1180px', margin: '0 auto', padding: '28px 24px' }}>
      {/* CAPTCHA Modal if challenge active */}
      {waitingCaptchaLab && (
        <CaptchaModal
          runId={runId}
          lab={waitingCaptchaLab}
          onResolved={() => {
            fetchRunDetails(runId).then(setDetails);
          }}
        />
      )}

      {/* Header Info */}
      {pollError && (
        <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px' }}>
          Polling notice: {pollError}
        </div>
      )}

      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '22px' }}>Patient: {run.patient_name}</h1>
              <span className={`badge badge-${run.status}`}>
                {run.status.replace(/_/g, ' ')}
              </span>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>ID: {run.patient_id || 'Not specified'}</span>
              <span style={{ margin: '0 8px' }}>•</span>
              <span>Range: {run.date_from} to {run.date_to}</span>
              <span style={{ margin: '0 8px' }}>•</span>
              <span>Portals: {run.labs.join(', ')}</span>
            </div>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textAlign: 'right' }}>
            <div>Run ID: <code style={{ color: '#cbd5e1' }}>{run.id}</code></div>
            <div>Key: <code style={{ color: '#cbd5e1' }}>{run.patient_key}</code></div>
          </div>
        </div>

        {/* Decision Counts Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '14px',
          marginTop: '22px',
          paddingTop: '20px',
          borderTop: '1px solid var(--border-color)'
        }}>
          <div style={{ background: 'var(--color-keep-bg)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-keep)', fontSize: '13px', fontWeight: 600 }}>
              <CheckCircle size={16} />
              <span>Keep (Unique)</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{counts.keep}</div>
          </div>

          <div style={{ background: 'var(--color-review-bg)', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-review)', fontSize: '13px', fontWeight: 600 }}>
              <HelpCircle size={16} />
              <span>Needs Review</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{counts.needs_review}</div>
          </div>

          <div style={{ background: 'var(--color-duplicate-bg)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-duplicate)', fontSize: '13px', fontWeight: 600 }}>
              <Copy size={16} />
              <span>Duplicate</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{counts.duplicate}</div>
          </div>

          <div style={{ background: 'var(--color-exclude-bg)', border: '1px solid rgba(244, 63, 94, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-exclude)', fontSize: '13px', fontWeight: 600 }}>
              <Ban size={16} />
              <span>Excluded</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{counts.exclude}</div>
          </div>

          <div style={{ background: 'var(--color-reject-bg)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-reject)', fontSize: '13px', fontWeight: 600 }}>
              <XCircle size={16} />
              <span>Rejected</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{counts.reject}</div>
          </div>
        </div>
      </div>

      {/* Live Agent Log */}
      <div style={{ marginBottom: '24px' }}>
        <LiveLog events={events} runStatus={run.status} />
      </div>

      {/* Approval Section */}
      {isWaitingApproval && (
        <ApprovalPanel
          candidates={candidates}
          onApprove={handleApprove}
          loading={approving}
        />
      )}

      {/* Result Table once run completes */}
      {isCompleted && (
        <div className="glass-panel" style={{ padding: '24px', marginTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <FileCheck2 size={22} color="#10b981" />
            <h2 style={{ fontSize: '18px' }}>Collection Completed Successfully</h2>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
            All approved reports were written to the permanent health timeline and re-verified against raw document bytes.
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-color)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px' }}>Lab</th>
                  <th style={{ padding: '12px' }}>Test / Investigation</th>
                  <th style={{ padding: '12px' }}>Report ID</th>
                  <th style={{ padding: '12px' }}>Date</th>
                  <th style={{ padding: '12px' }}>Status</th>
                  <th style={{ padding: '12px' }}>Re-Check Verification</th>
                  <th style={{ padding: '12px' }}>Document</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => {
                  const pdfUrl = getPdfFileUrl(c.id);
                  return (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '12px', fontWeight: 600 }}>{c.lab}</td>
                      <td style={{ padding: '12px', color: '#fff' }}>{c.x_test || c.listing_title}</td>
                      <td style={{ padding: '12px', color: '#94a3b8' }}>{c.x_report_id || c.portal_report_id}</td>
                      <td style={{ padding: '12px', color: '#94a3b8' }}>{c.x_date || c.portal_date}</td>
                      <td style={{ padding: '12px' }}>
                        <span className={`badge badge-${c.decision}`}>
                          {c.decision}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        {c.recheck_ok === true && (
                          <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
                            <ShieldCheck size={14} />
                            <span>Verified</span>
                          </span>
                        )}
                        {c.recheck_ok === false && (
                          <span style={{ color: '#f87171', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
                            <AlertCircle size={14} />
                            <span>Failed re-check</span>
                          </span>
                        )}
                        {c.recheck_ok === undefined && (
                          <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Not stored</span>
                        )}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <a
                          href={pdfUrl}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: '#818cf8', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none' }}
                        >
                          <span>PDF</span>
                          <ExternalLink size={12} />
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
