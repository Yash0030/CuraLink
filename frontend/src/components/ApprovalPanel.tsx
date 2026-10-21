import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Copy, Ban, ExternalLink } from 'lucide-react';
import type { CandidateItem } from '../types';
import { getPdfFileUrl } from '../api';

interface ApprovalPanelProps {
  candidates: CandidateItem[];
  onApprove: (approved: boolean, overrides: Record<string, string>) => Promise<void>;
  loading: boolean;
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({ candidates, onApprove, loading }) => {
  // Store user decisions for "needs_review" items: candidate_id -> "keep" | "skip"
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  // Group candidates
  const willBeSaved = candidates.filter(c => c.decision === 'keep');
  const needsDecision = candidates.filter(c => c.decision === 'needs_review');
  const duplicates = candidates.filter(c => c.decision === 'duplicate');
  const excluded = candidates.filter(c => c.decision === 'exclude');
  const rejected = candidates.filter(c => c.decision === 'reject');

  // Check if all "needs_review" candidates have a selected decision
  const pendingDecisionsCount = needsDecision.filter(c => !overrides[c.id]).length;
  const canApprove = pendingDecisionsCount === 0;

  const handleDecisionChange = (candidateId: string, choice: 'keep' | 'skip') => {
    setOverrides(prev => ({
      ...prev,
      [candidateId]: choice
    }));
  };

  const handleApproveAll = async () => {
    if (!canApprove) {
      setError(`Please resolve all ${pendingDecisionsCount} pending decisions before approving.`);
      return;
    }
    setError(null);
    await onApprove(true, overrides);
  };

  const handleRejectRun = async () => {
    if (window.confirm("Are you sure you want to reject this collection run? Nothing will be saved.")) {
      await onApprove(false, {});
    }
  };

  const renderCandidateRow = (c: CandidateItem, allowOverride: boolean = false) => {
    const pdfUrl = getPdfFileUrl(c.id);
    const labName = c.lab === 'labA' ? 'A1' : c.lab === 'labB' ? 'CityScan' : 'Vitals';

    return (
      <div
        key={c.id}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'rgba(15, 23, 42, 0.4)',
          borderBottom: '1px solid var(--border-color)',
          fontSize: '13px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1 }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 600,
            padding: '2px 7px',
            borderRadius: '4px',
            background: 'rgba(255, 255, 255, 0.08)',
            color: '#94a3b8'
          }}>
            {labName}
          </span>

          <div>
            <div style={{ fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>{c.x_test || c.listing_title || 'Medical Report'}</span>
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#818cf8', display: 'inline-flex', alignItems: 'center', gap: '3px', fontSize: '11px', textDecoration: 'none' }}
              >
                <span>View PDF</span>
                <ExternalLink size={11} />
              </a>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              <span>ID: {c.x_report_id || c.portal_report_id || 'N/A'}</span>
              <span style={{ margin: '0 6px' }}>•</span>
              <span>Date: {c.x_date || c.portal_date || 'N/A'}</span>
              <span style={{ margin: '0 6px' }}>•</span>
              <span>Patient: {c.x_name || 'N/A'}</span>
            </div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px', fontStyle: 'italic' }}>
              Reason: {c.decision_reason || 'Verified'}
            </div>
          </div>
        </div>

        {allowOverride && (
          <div style={{ marginLeft: '16px' }}>
            <select
              value={overrides[c.id] || ''}
              onChange={e => handleDecisionChange(c.id, e.target.value as 'keep' | 'skip')}
              className="input-field"
              style={{
                padding: '6px 12px',
                fontSize: '13px',
                background: overrides[c.id] === 'keep' ? 'rgba(16, 185, 129, 0.2)' : overrides[c.id] === 'skip' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(30, 41, 59, 0.8)',
                borderColor: overrides[c.id] ? (overrides[c.id] === 'keep' ? '#10b981' : '#ef4444') : '#6366f1'
              }}
            >
              <option value="" disabled>Select decision...</option>
              <option value="keep">Keep (Save to Record)</option>
              <option value="skip">Skip (Do Not Save)</option>
            </select>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginTop: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px' }}>Human Approval Required</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Review candidate reports and approve changes before writing to permanent patient record.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={handleRejectRun}
            className="btn btn-danger"
            disabled={loading}
          >
            Reject All
          </button>
          <button
            type="button"
            onClick={handleApproveAll}
            className="btn btn-primary"
            disabled={!canApprove || loading}
            style={{ opacity: canApprove ? 1 : 0.6 }}
          >
            {loading ? 'Processing...' : 'Approve & Save Records'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          padding: '10px 14px',
          borderRadius: '8px',
          fontSize: '13px',
          marginBottom: '20px'
        }}>
          {error}
        </div>
      )}

      {/* Group 1: Needs Your Decision */}
      {needsDecision.length > 0 && (
        <div style={{ marginBottom: '24px', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{
            background: 'rgba(168, 85, 247, 0.15)',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', fontWeight: 600, fontSize: '14px' }}>
              <AlertTriangle size={18} />
              <span>Needs Your Decision ({needsDecision.length})</span>
            </div>
            {pendingDecisionsCount > 0 && (
              <span style={{ fontSize: '12px', color: '#e9d5ff', background: 'rgba(168, 85, 247, 0.3)', padding: '2px 8px', borderRadius: '4px' }}>
                {pendingDecisionsCount} unresolved decision{pendingDecisionsCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div>{needsDecision.map(c => renderCandidateRow(c, true))}</div>
        </div>
      )}

      {/* Group 2: Will Be Saved */}
      <div style={{ marginBottom: '24px', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', overflow: 'hidden' }}>
        <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 600, fontSize: '14px' }}>
          <CheckCircle2 size={18} />
          <span>Will Be Saved ({willBeSaved.length})</span>
        </div>
        {willBeSaved.length === 0 ? (
          <div style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '13px' }}>No automatic keep candidates.</div>
        ) : (
          <div>{willBeSaved.map(c => renderCandidateRow(c, false))}</div>
        )}
      </div>

      {/* Group 3: Duplicates */}
      {duplicates.length > 0 && (
        <div style={{ marginBottom: '24px', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', fontWeight: 600, fontSize: '14px' }}>
            <Copy size={18} />
            <span>Duplicates ({duplicates.length}) — Will not be saved</span>
          </div>
          <div>{duplicates.map(c => renderCandidateRow(c, false))}</div>
        </div>
      )}

      {/* Group 4: Excluded */}
      {excluded.length > 0 && (
        <div style={{ marginBottom: '24px', border: '1px solid rgba(244, 63, 94, 0.25)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'rgba(244, 63, 94, 0.1)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#fb7185', fontWeight: 600, fontSize: '14px' }}>
            <Ban size={18} />
            <span>Excluded (Different Patient / Look-alike) ({excluded.length})</span>
          </div>
          <div>{excluded.map(c => renderCandidateRow(c, false))}</div>
        </div>
      )}

      {/* Group 5: Rejected */}
      {rejected.length > 0 && (
        <div style={{ border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 600, fontSize: '14px' }}>
            <XCircle size={18} />
            <span>Rejected (Invalid PDF / Corrupt / Out of Range) ({rejected.length})</span>
          </div>
          <div>{rejected.map(c => renderCandidateRow(c, false))}</div>
        </div>
      )}
    </div>
  );
};
