import React, { useEffect, useState, useRef } from 'react';
import {
  FileCheck2,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import type { RunDetailsResponse, CandidateItem, EventLogItem } from '../types';
import {
  fetchRunDetails,
  fetchRunEvents,
  fetchRunCandidates,
  submitApproval,
  getPdfFileUrl,
  cancelRun
} from '../api';
import { ApprovalPanel } from './ApprovalPanel';
import { CaptchaModal } from './CaptchaModal';
import { PdfModal } from './PdfModal';

interface RunViewProps {
  runId: string;
  onRunCompleted: () => void;
  onCancelRun?: () => void;
}

export const RunView: React.FC<RunViewProps> = ({ runId, onRunCompleted, onCancelRun }) => {
  const [details, setDetails] = useState<RunDetailsResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [events, setEvents] = useState<EventLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);
  const [activePdf, setActivePdf] = useState<{ url: string; title: string } | null>(null);
  const activityListRef = useRef<HTMLOListElement>(null);

  // Poll run details and events every 1.5 seconds
  useEffect(() => {
    let isMounted = true;
    let timer: any = null;

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

          const isTerm = det.run.status === 'completed' || det.run.status === 'failed' || det.run.status === 'cancelled' || det.run.status === 'rejected_by_human';
          if (isTerm) {
            if (det.run.status === 'completed') {
              onRunCompleted();
            }
            if (timer) clearInterval(timer);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setPollError(err.message || 'Failed to poll run data');
          if (err.message?.includes('404') || err.message?.includes('Not Found')) {
            if (timer) clearInterval(timer);
          }
        }
      }
    };

    loadData();
    timer = setInterval(loadData, 1500);

    return () => {
      isMounted = false;
      if (timer) clearInterval(timer);
    };
  }, [runId]);

  const handleApprove = async (approved: boolean, overrides: Record<string, string>) => {
    setApproving(true);
    try {
      await submitApproval(runId, approved, overrides);
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

  const formatRunDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const formatEventTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString(undefined, {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const formatActorBadge = (agent: string) => {
    const isUser = agent === 'User' || agent === 'User Action' || agent === 'Human';
    if (isUser) {
      return (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '6px',
          fontSize: '11px',
          fontWeight: 700,
          background: 'rgba(20, 184, 166, 0.16)',
          color: 'var(--primary-hover)',
          border: '1px solid rgba(20, 184, 166, 0.4)',
          width: 'fit-content',
          textTransform: 'uppercase',
          letterSpacing: '0.04em'
        }}>
          👤 Human (You)
        </span>
      );
    }

    let agentLabel = agent;
    if (agent.startsWith('Fetcher-')) {
      const labCode = agent.replace('Fetcher-', '');
      const labName = labCode === 'labA' ? 'A1' : labCode === 'labB' ? 'CityScan' : labCode === 'labC' ? 'Vitals' : labCode;
      agentLabel = `Fetcher (${labName})`;
    } else if (agent === 'Checker' || agent === 'Verifier') {
      agentLabel = 'Verifier & Duplicate Checker';
    } else if (agent === 'Orchestrator') {
      agentLabel = 'Orchestrator';
    } else if (agent === 'Extractor') {
      agentLabel = 'Extractor';
    } else if (agent === 'Storage') {
      agentLabel = 'Storage';
    }

    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 8px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: 650,
        background: 'rgba(99, 102, 241, 0.14)',
        color: '#a5b4fc',
        border: '1px solid rgba(99, 102, 241, 0.32)',
        width: 'fit-content',
        textTransform: 'uppercase',
        letterSpacing: '0.03em'
      }}>
        🤖 Agent: {agentLabel}
      </span>
    );
  };

  if (loading && !details) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px', color: '#3A4A5E' }}>
        <svg className="spin" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0B7A75" strokeWidth="2.4" strokeLinecap="round" style={{ margin: '0 auto 16px', display: 'block' }}>
          <path d="M12 3a9 9 0 1 0 9 9"></path>
        </svg>
        <p style={{ fontSize: '15px' }}>Connecting to collection run {runId}...</p>
      </div>
    );
  }

  if (!details) {
    return (
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '40px 32px',
        textAlign: 'center'
      }}>
        <h3 style={{ fontSize: '18px', fontWeight: 650, color: 'var(--text-main)', marginBottom: '8px' }}>
          Collection run not found
        </h3>
        <p style={{ fontSize: '14.5px', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto 20px' }}>
          This run may have ended or was initiated in another session.
        </p>
        {onCancelRun && (
          <button type="button" onClick={onCancelRun} className="btn primary">
            Back to Active run
          </button>
        )}
      </div>
    );
  }

  const run = details.run;
  const isWaitingApproval = run.status === 'waiting_approval';
  const isCompleted = run.status === 'completed';
  const isCancelled = run.status === 'cancelled' || run.status === 'rejected_by_human';
  const isFailed = run.status === 'failed';
  const isTerminal = isCompleted || isCancelled || isFailed;
  const waitingCaptchaLab = details.waiting_captchas?.[0];

  const handleCancelClick = async () => {
    if (isTerminal) {
      onCancelRun?.();
      return;
    }

    const confirmed = window.confirm("Are you sure you want to cancel this collection run? Any ongoing downloads will be stopped.");
    if (!confirmed) return;

    try {
      setCancelling(true);
      await cancelRun(runId);
      const [det, cand, evs] = await Promise.all([
        fetchRunDetails(runId),
        fetchRunCandidates(runId),
        fetchRunEvents(runId, 0)
      ]);
      setDetails(det);
      setCandidates(cand);
      setEvents(evs);
    } catch (err: any) {
      console.error("Cancel run error:", err);
      alert("Failed to cancel run: " + (err.message || String(err)));
    } finally {
      setCancelling(false);
    }
  };

  // Helper to determine step status
  const getLabStatus = (labId: string) => {
    const isWaitingCaptcha = waitingCaptchaLab === labId;
    const labEvents = events.filter(e => e.agent?.toLowerCase().includes(labId.toLowerCase()) || e.message.toLowerCase().includes(labId.toLowerCase()));
    const hasFinished = labEvents.some(e => e.message.toLowerCase().includes('done') || e.message.toLowerCase().includes('downloaded') || e.message.toLowerCase().includes('complete'));
    const isWorking = isWaitingCaptcha || labEvents.some(e => e.message.toLowerCase().includes('login') || e.message.toLowerCase().includes('signed in') || e.message.toLowerCase().includes('found'));

    if (isCompleted || hasFinished) {
      const count = candidates.filter(c => c.lab.toLowerCase() === labId.toLowerCase()).length;
      return {
        state: 'done',
        text: count > 0 ? `${count} report${count > 1 ? 's' : ''} downloaded` : 'Collection completed'
      };
    }
    if (isCancelled) {
      return { state: 'waiting', text: 'Cancelled' };
    }
    if (isWaitingCaptcha) {
      return { state: 'working', text: 'Solving the CAPTCHA to sign in' };
    }
    if (isWorking || run.status === 'running') {
      return { state: 'working', text: 'Signing in and searching reports' };
    }
    return { state: 'waiting', text: 'Waiting to connect' };
  };

  const getLabName = (labId: string) => {
    if (labId === 'a1' || labId === 'labA') return 'A1 Diagnostics';
    if (labId === 'cityscan' || labId === 'labB') return 'CityScan Imaging';
    if (labId === 'vitals' || labId === 'labC') return 'Vitals Laboratory';
    return labId;
  };

  // Determine overall run stage
  let stepNumber = 1;
  let stepLabel = 'Signing in to lab portals';
  let progressPct = 25;

  if (run.status === 'running') {
    stepNumber = 2;
    stepLabel = 'Collecting from labs';
    progressPct = 50;
  } else if (run.status === 'checking') {
    stepNumber = 3;
    stepLabel = 'Reading PDFs and checking records';
    progressPct = 75;
  } else if (run.status === 'waiting_approval') {
    stepNumber = 4;
    stepLabel = 'Waiting for your review';
    progressPct = 90;
  } else if (run.status === 'completed') {
    stepNumber = 4;
    stepLabel = 'Collection complete';
    progressPct = 100;
  } else if (isCancelled) {
    stepNumber = 4;
    stepLabel = 'Collection cancelled';
    progressPct = 100;
  } else if (isFailed) {
    stepNumber = 4;
    stepLabel = 'Collection failed';
    progressPct = 100;
  }

  const labsCompletedCount = run.labs.filter(l => getLabStatus(l).state === 'done').length;

  return (
    <>
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

      {/* Notice banner if polling error */}
      {pollError && (
        <div style={{ background: '#FEE2E2', border: '1px solid #FCA5A5', color: '#991B1B', padding: '10px 16px', borderRadius: '10px', fontSize: '13px' }}>
          Notice: {pollError}
        </div>
      )}

      {/* Header - exactly matches A_ActiveRun.dc.html */}
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '30px', lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.01em' }}>
            Collecting for {run.patient_name}
          </h1>
          <p style={{ margin: '8px 0 0', fontSize: '15px', lineHeight: 1.5, color: '#3A4A5E' }}>
            Patient ID {run.patient_id || 'pt001'}, {run.date_from} to {run.date_to}. Started {formatRunDate(run.created_at)}.
          </p>
        </div>
        {onCancelRun && (
          <button
            type="button"
            onClick={handleCancelClick}
            disabled={cancelling}
            className={`btn ${isTerminal ? 'primary' : 'danger'}`}
            style={{ minHeight: '40px' }}
          >
            {cancelling ? 'Cancelling...' : isTerminal ? 'Exit run' : 'Cancel run'}
          </button>
        )}
      </header>

      {/* Cancellation Notice Banner */}
      {isCancelled && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          color: 'var(--text-main)',
          padding: '14px 20px',
          borderRadius: '12px',
          fontSize: '14.5px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', flexShrink: 0 }}></div>
          <span><strong>Run Cancelled:</strong> This collection run was stopped by user request. Any pending downloads were terminated.</span>
        </div>
      )}

      {/* Overall progress - matches A_ActiveRun.dc.html */}
      <section aria-label="Progress" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '14px', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14.5px', fontWeight: 600 }}>
          <span>Step {stepNumber} of 4: {stepLabel}</span>
          <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
            {labsCompletedCount} of {run.labs.length} labs done
          </span>
        </div>
        <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPct} aria-label="Run progress" style={{ height: '8px', borderRadius: '4px', background: 'var(--border-color)', overflow: 'hidden' }}>
          <div style={{ width: `${progressPct}%`, height: '100%', background: 'var(--primary)', transition: 'width 0.4s ease' }}></div>
        </div>
      </section>

      {/* Two Column Section - matches A_ActiveRun.dc.html */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px', alignItems: 'flex-start' }}>
        {/* Steps Card */}
        <section style={{ flex: '1 1 420px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-muted)', paddingLeft: '4px' }}>Steps</h2>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '14px', overflow: 'hidden' }}>
            {/* Lab Steps */}
            {run.labs.map(labId => {
              const info = getLabStatus(labId);
              return (
                <div key={labId} className="step" style={{ background: info.state === 'working' ? 'var(--bg-active)' : 'var(--bg-card)' }}>
                  {info.state === 'done' ? (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="9"></circle>
                      <path d="M8 12.5l3 3 5-6"></path>
                    </svg>
                  ) : info.state === 'working' ? (
                    <svg className="spin" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
                      <path d="M12 3a9 9 0 1 0 9 9"></path>
                    </svg>
                  ) : (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2" aria-hidden="true">
                      <circle cx="12" cy="12" r="9"></circle>
                    </svg>
                  )}
                  <div style={{ flex: 1, lineHeight: 1.35 }}>
                    <div style={{ fontSize: '16px', fontWeight: 650, color: 'var(--text-main)' }}>{getLabName(labId)}</div>
                    <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>{info.text}</div>
                  </div>
                  <span className="st" style={{ color: info.state === 'waiting' ? 'var(--text-muted)' : 'var(--primary-dark)' }}>
                    {info.state === 'done' ? 'Done' : info.state === 'working' ? 'Working' : 'Waiting'}
                  </span>
                </div>
              );
            })}

            {/* Read PDFs Step */}
            <div className="step" style={{ background: (stepNumber === 3) ? 'var(--bg-active)' : 'var(--bg-card)' }}>
              {stepNumber >= 4 ? (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9"></circle>
                  <path d="M8 12.5l3 3 5-6"></path>
                </svg>
              ) : stepNumber === 3 ? (
                <svg className="spin" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
                  <path d="M12 3a9 9 0 1 0 9 9"></path>
                </svg>
              ) : (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="9"></circle>
                </svg>
              )}
              <div style={{ flex: 1, lineHeight: 1.35 }}>
                <div style={{ fontSize: '16px', fontWeight: 650, color: 'var(--text-main)' }}>Read PDFs</div>
                <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  {stepNumber >= 4 ? 'All documents read and indexed' : 'Starts when downloads finish'}
                </div>
              </div>
              <span className="st" style={{ color: stepNumber < 3 ? 'var(--text-muted)' : 'var(--primary-dark)' }}>
                {stepNumber >= 4 ? 'Done' : stepNumber === 3 ? 'Working' : 'Waiting'}
              </span>
            </div>

            {/* Check records Step */}
            <div className="step" style={{ background: 'var(--bg-card)' }}>
              {isCompleted ? (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9"></circle>
                  <path d="M8 12.5l3 3 5-6"></path>
                </svg>
              ) : isWaitingApproval ? (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9"></circle>
                  <path d="M8 12.5l3 3 5-6"></path>
                </svg>
              ) : (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="9"></circle>
                </svg>
              )}
              <div style={{ flex: 1, lineHeight: 1.35 }}>
                <div style={{ fontSize: '16px', fontWeight: 650, color: 'var(--text-main)' }}>Check records</div>
                <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                  Finds duplicates and reports for the wrong patient
                </div>
              </div>
              <span className="st" style={{ color: isCompleted || isWaitingApproval ? 'var(--primary-dark)' : 'var(--text-muted)' }}>
                {isCompleted ? 'Done' : isWaitingApproval ? 'Ready for review' : 'Waiting'}
              </span>
            </div>
          </div>
        </section>

        {/* Activity Card */}
        <section style={{ flex: '1 1 340px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
            <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-muted)' }}>Activity</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{events.length} event{events.length !== 1 ? 's' : ''}</span>
          </div>
          <ol
            ref={activityListRef}
            style={{
              listStyle: 'none',
              margin: 0,
              padding: '8px 0',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '14px',
              maxHeight: '420px',
              overflowY: 'auto'
            }}
          >
            {events.length === 0 ? (
              <li style={{ padding: '16px 20px', fontSize: '14px', color: 'var(--text-dim)' }}>
                Connecting to lab portals...
              </li>
            ) : (
              events.map((l) => {
                const isUser = l.agent === 'User' || l.agent === 'User Action' || l.agent === 'Human';
                return (
                  <li
                    key={l.id}
                    style={{
                      display: 'flex',
                      gap: '12px',
                      alignItems: 'flex-start',
                      padding: '10px 18px',
                      fontSize: '14px',
                      lineHeight: 1.45,
                      background: isUser ? 'rgba(20, 184, 166, 0.08)' : undefined,
                      borderLeft: isUser ? '3px solid var(--primary)' : '3px solid transparent',
                      transition: 'background 0.15s ease'
                    }}
                  >
                    <span style={{ flex: '0 0 68px', color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums', fontSize: '12.5px', marginTop: '3px' }}>
                      {formatEventTime(l.created_at)}
                    </span>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {formatActorBadge(l.agent)}
                      </div>
                      <span style={{ color: 'var(--text-main)', fontWeight: isUser ? 550 : 400, wordBreak: 'break-word' }}>
                        {l.message}
                      </span>
                    </div>
                  </li>
                );
              })
            )}
          </ol>
        </section>
      </div>

      {/* Human Approval Required Section */}
      {isWaitingApproval && (
        <ApprovalPanel
          candidates={candidates}
          onApprove={handleApprove}
          loading={approving}
        />
      )}

      {/* Result Table once run completes */}
      {isCompleted && (
        <section style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileCheck2 size={24} color="var(--primary)" />
            <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
              Collection completed successfully
            </h2>
          </div>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: 0 }}>
            All approved reports were written to the permanent health timeline and re-verified against raw document bytes.
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Lab</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Test / Investigation</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Report ID</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Date</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Verification</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Document</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => {
                  const pdfUrl = getPdfFileUrl(c.id);
                  return (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '12px 14px', fontWeight: 600, color: 'var(--text-main)' }}>{getLabName(c.lab)}</td>
                      <td style={{ padding: '12px 14px', color: 'var(--text-main)', fontWeight: 600 }}>
                        {c.x_test || c.listing_title}
                      </td>
                      <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                        {c.x_report_id || c.portal_report_id}
                      </td>
                      <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                        {c.x_date || c.portal_date}
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        <span className={`status ${c.decision === 'keep' ? 's-done' : c.decision === 'needs_review' ? 's-wait' : 's-pend'}`}>
                          {c.decision}
                        </span>
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        {c.recheck_ok === true && (
                          <span style={{ color: '#074F4B', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', fontWeight: 600 }}>
                            <ShieldCheck size={16} />
                            <span>Verified</span>
                          </span>
                        )}
                        {c.recheck_ok === false && (
                          <span style={{ color: '#991B1B', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', fontWeight: 600 }}>
                            <AlertCircle size={16} />
                            <span>Failed re-check</span>
                          </span>
                        )}
                        {c.recheck_ok === undefined && (
                          <span style={{ color: '#4A5A6E', fontSize: '13px' }}>Not stored</span>
                        )}
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        <button
                          type="button"
                          onClick={() => setActivePdf({
                            url: pdfUrl,
                            title: `${c.x_test || c.listing_title || 'Report'} (${c.lab})`
                          })}
                          className="btn"
                          style={{ minHeight: '34px', padding: '0 12px', fontSize: '13px' }}
                        >
                          View PDF
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* In-app PDF Viewer Modal */}
      <PdfModal
        isOpen={Boolean(activePdf)}
        pdfUrl={activePdf?.url || null}
        title={activePdf?.title}
        onClose={() => setActivePdf(null)}
      />
    </>
  );
};
