import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Copy,
  Ban,
  FileText,
  Check,
  X
} from 'lucide-react';
import type { CandidateItem } from '../types';
import { getPdfFileUrl } from '../api';
import { PdfModal } from './PdfModal';
import { useConfirm } from './ConfirmModal';

interface ApprovalPanelProps {
  candidates: CandidateItem[];
  onApprove: (approved: boolean, overrides: Record<string, string>) => Promise<void>;
  loading: boolean;
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({ candidates, onApprove, loading }) => {
  const { confirm } = useConfirm();
  // Store user decisions per candidate: candidate_id -> "keep" | "reject"
  const [overrides, setOverrides] = useState<Record<string, 'keep' | 'reject'>>({});
  // Set of selected candidate IDs (for bulk selection and bulk actions)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [activePdf, setActivePdf] = useState<{ url: string; title: string } | null>(null);

  // Helper to determine whether an item will be saved
  const getDecision = (c: CandidateItem): 'keep' | 'reject' => {
    if (overrides[c.id]) {
      return overrides[c.id];
    }
    // Default: 'keep' for automatic keep, 'reject' for duplicate/exclude/reject/needs_review
    return c.decision === 'keep' ? 'keep' : 'reject';
  };

  const handleDecisionChange = (candidateId: string, choice: 'keep' | 'reject') => {
    setOverrides(prev => ({
      ...prev,
      [candidateId]: choice
    }));
  };

  // Selection handlers
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === candidates.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(candidates.map(c => c.id)));
    }
  };

  // Bulk actions on selected items
  const handleAcceptSelected = () => {
    setOverrides(prev => {
      const next = { ...prev };
      selectedIds.forEach(id => {
        next[id] = 'keep';
      });
      return next;
    });
    setSelectedIds(new Set());
  };

  const handleSaveSelectedNow = async () => {
    if (selectedIds.size === 0) return;
    setError(null);
    const finalOverrides: Record<string, string> = {};
    candidates.forEach(c => {
      finalOverrides[c.id] = selectedIds.has(c.id) ? 'keep' : 'reject';
    });
    await onApprove(true, finalOverrides);
  };

  const handleRejectSelected = () => {
    setOverrides(prev => {
      const next = { ...prev };
      selectedIds.forEach(id => {
        next[id] = 'reject';
      });
      return next;
    });
    setSelectedIds(new Set());
  };

  // Global quick actions
  const handleAcceptAll = () => {
    const next: Record<string, 'keep' | 'reject'> = {};
    candidates.forEach(c => {
      next[c.id] = 'keep';
    });
    setOverrides(next);
  };

  const handleRejectAll = () => {
    const next: Record<string, 'keep' | 'reject'> = {};
    candidates.forEach(c => {
      next[c.id] = 'reject';
    });
    setOverrides(next);
  };

  // Calculate live counts
  const totalWillBeSaved = candidates.filter(c => getDecision(c) === 'keep').length;
  const totalWillBeRejected = candidates.length - totalWillBeSaved;

  // Unresolved needs_review items that user hasn't explicitly decided on
  const needsDecision = candidates.filter(c => c.decision === 'needs_review');
  const unresolvedNeedsReview = needsDecision.filter(c => !overrides[c.id]);

  const handleApproveSelected = async () => {
    if (unresolvedNeedsReview.length > 0) {
      setError(`Please decide on all ${unresolvedNeedsReview.length} reports needing your review before proceeding.`);
      return;
    }
    setError(null);

    if (totalWillBeSaved === 0) {
      const confirmed = await confirm({
        title: 'Reject Collection Run',
        message: 'No PDF reports are marked to be saved. Reject this collection run?',
        confirmText: 'Reject Run',
        cancelText: 'Keep Editing',
        isDanger: true,
      });
      if (confirmed) {
        await onApprove(false, {});
      }
      return;
    }

    // Prepare complete overrides dictionary for backend
    const finalOverrides: Record<string, string> = {};
    candidates.forEach(c => {
      finalOverrides[c.id] = getDecision(c);
    });

    await onApprove(true, finalOverrides);
  };

  const handleRejectEntireRun = async () => {
    const confirmed = await confirm({
      title: 'Reject Entire Collection Run',
      message: 'Are you sure you want to reject this entire collection run? None of the reports will be saved.',
      confirmText: 'Reject All Reports',
      cancelText: 'Cancel',
      isDanger: true,
    });
    if (confirmed) {
      await onApprove(false, {});
    }
  };

  // Group candidates for structured display
  const willBeSavedOriginal = candidates.filter(c => c.decision === 'keep');
  const duplicates = candidates.filter(c => c.decision === 'duplicate');
  const excluded = candidates.filter(c => c.decision === 'exclude');
  const rejected = candidates.filter(c => c.decision === 'reject');

  const renderCandidateRow = (c: CandidateItem) => {
    const pdfUrl = getPdfFileUrl(c.id);
    const labName =
      c.lab === 'labA'
        ? 'A1 Diagnostics'
        : c.lab === 'labB'
        ? 'CityScan Imaging'
        : c.lab === 'labC'
        ? 'Vitals Laboratory'
        : c.lab;

    const isAccepted = getDecision(c) === 'keep';
    const isSelected = selectedIds.has(c.id);

    return (
      <div
        key={c.id}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: isSelected ? 'var(--primary-light)' : isAccepted ? 'var(--bg-card)' : 'var(--bg-subtle)',
          borderTop: '1px solid var(--border-color)',
          fontSize: '13.5px',
          transition: 'background-color 0.15s ease',
          opacity: isAccepted ? 1 : 0.78
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: 0 }}>
          {/* Row Checkbox for multi-selection */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleSelect(c.id)}
            aria-label={`Select ${c.x_test || c.listing_title || 'document'}`}
            style={{
              width: '18px',
              height: '18px',
              cursor: 'pointer',
              accentColor: 'var(--primary)',
              flexShrink: 0
            }}
          />

          {/* Lab Tag */}
          <span
            className="tag"
            style={{
              background: 'var(--primary-light)',
              color: 'var(--primary-dark)',
              flexShrink: 0,
              fontSize: '12px',
              fontWeight: 650
            }}
          >
            {labName}
          </span>

          {/* Document Details */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span
                style={{
                  fontWeight: 650,
                  color: isAccepted ? 'var(--text-main)' : 'var(--text-dim)',
                  textDecoration: isAccepted ? 'none' : 'line-through'
                }}
              >
                {c.x_test || c.listing_title || 'Medical Report'}
              </span>

              {/* Clickable PDF Filename button */}
              <button
                type="button"
                onClick={() =>
                  setActivePdf({
                    url: pdfUrl,
                    title: `${c.filename} — ${c.x_test || c.listing_title || 'Report'} (${c.lab})`
                  })
                }
                title={`Click filename ${c.filename} to preview PDF`}
                data-testid={`btn-view-pdf-${c.id}`}
                style={{
                  background: 'rgba(20, 184, 166, 0.08)',
                  border: '1px solid rgba(20, 184, 166, 0.28)',
                  color: 'var(--primary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '12px',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  fontWeight: 650,
                  padding: '3px 8px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  textUnderlineOffset: '2px',
                  transition: 'all 0.15s ease'
                }}
              >
                <FileText size={13} style={{ flexShrink: 0 }} />
                <span>{c.filename}</span>
              </button>

              {/* Decision Badge */}
              {isAccepted ? (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11.5px',
                    fontWeight: 650,
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: 'var(--primary-surface)',
                    color: 'var(--primary-dark)'
                  }}
                >
                  <Check size={11} strokeWidth={3} />
                  Will Save
                </span>
              ) : (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11.5px',
                    fontWeight: 650,
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: 'var(--s-fail-bg)',
                    color: 'var(--s-fail-text)'
                  }}
                >
                  <X size={11} strokeWidth={3} />
                  Will Reject
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '4px 8px', fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              <span>ID: <strong style={{ color: 'var(--text-main)', fontWeight: 600 }}>{c.x_report_id || c.portal_report_id || 'N/A'}</strong></span>
              <span>•</span>
              <span>Date: <strong style={{ color: 'var(--text-main)', fontWeight: 600 }}>{c.x_date || c.portal_date || 'N/A'}</strong></span>
              <span>•</span>
              <span>Patient: <strong style={{ color: 'var(--text-main)', fontWeight: 600 }}>{c.x_name || 'N/A'}</strong></span>
              <span>•</span>
              <button
                type="button"
                onClick={() =>
                  setActivePdf({
                    url: pdfUrl,
                    title: `${c.filename} — ${c.x_test || c.listing_title || 'Report'} (${c.lab})`
                  })
                }
                title={`Open and inspect ${c.filename}`}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  color: 'var(--primary)',
                  cursor: 'pointer',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  textDecoration: 'underline',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px'
                }}
              >
                Inspect file &rarr;
              </button>
            </div>

            {c.decision_reason && (
              <div style={{
                fontSize: '12.5px',
                marginTop: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: c.decision === 'duplicate'
                  ? 'rgba(59, 130, 246, 0.12)'
                  : c.decision === 'keep'
                  ? 'rgba(20, 184, 166, 0.08)'
                  : 'rgba(239, 68, 68, 0.12)',
                border: c.decision === 'duplicate'
                  ? '1px solid rgba(59, 130, 246, 0.28)'
                  : c.decision === 'keep'
                  ? '1px solid rgba(20, 184, 166, 0.22)'
                  : '1px solid rgba(239, 68, 68, 0.28)',
                color: c.decision === 'duplicate'
                  ? '#93c5fd'
                  : c.decision === 'keep'
                  ? 'var(--primary)'
                  : '#fca5a5',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                lineHeight: 1.35
              }}>
                <AlertTriangle size={14} style={{ flexShrink: 0 }} />
                <span>
                  <strong>{c.decision === 'duplicate' ? 'Duplicate Report:' : c.decision === 'keep' ? 'Validation:' : 'Rejection Reason:'}</strong>{' '}
                  {c.decision_reason}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Individual Accept / Reject Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '16px', flexShrink: 0 }}>
          <button
            type="button"
            onClick={() => handleDecisionChange(c.id, 'keep')}
            aria-label={`Accept ${c.x_test || 'document'}`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12.5px',
              fontWeight: 650,
              cursor: 'pointer',
              background: isAccepted ? 'var(--primary)' : 'var(--bg-subtle)',
              color: isAccepted ? '#FFFFFF' : 'var(--text-main)',
              border: isAccepted ? '1px solid var(--primary)' : '1px solid var(--border-strong)',
              boxShadow: isAccepted ? '0 1px 2px rgba(11, 122, 117, 0.2)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            <Check size={13} strokeWidth={2.5} />
            <span>Accept</span>
          </button>

          <button
            type="button"
            onClick={() => handleDecisionChange(c.id, 'reject')}
            aria-label={`Reject ${c.x_test || 'document'}`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12.5px',
              fontWeight: 650,
              cursor: 'pointer',
              background: !isAccepted ? '#DC2626' : 'var(--bg-subtle)',
              color: !isAccepted ? '#FFFFFF' : 'var(--text-main)',
              border: !isAccepted ? '1px solid #DC2626' : '1px solid var(--border-strong)',
              boxShadow: !isAccepted ? '0 1px 2px rgba(220, 38, 38, 0.2)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            <X size={13} strokeWidth={2.5} />
            <span>Reject</span>
          </button>
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '24px',
        marginTop: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        boxShadow: 'var(--shadow-sm)'
      }}
    >
      {/* Header and Primary Actions */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          flexWrap: 'wrap'
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 750, color: 'var(--text-main)' }}>
            Human Approval Required
          </h3>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
            Review candidate reports. You can individually accept or reject any PDF, or select multiple documents to apply batch actions.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            type="button"
            onClick={handleRejectEntireRun}
            className="btn"
            disabled={loading}
            style={{
              color: '#DC2626',
              borderColor: '#FCA5A5',
              background: 'var(--s-fail-bg)',
              fontWeight: 650,
              padding: '8px 16px'
            }}
          >
            Reject All
          </button>

          <button
            type="button"
            onClick={handleApproveSelected}
            className="btn primary"
            disabled={loading}
            style={{
              background: 'var(--primary)',
              color: '#fff',
              fontWeight: 700,
              padding: '8px 20px',
              boxShadow: '0 2px 6px rgba(11, 122, 117, 0.3)'
            }}
          >
            {loading ? 'Processing...' : `Approve & Save Records (${totalWillBeSaved})`}
          </button>
        </div>
      </div>

      {/* Multi-Selection & Batch Actions Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'var(--bg-subtle)',
          borderRadius: '10px',
          border: '1px solid var(--border-color)',
          fontSize: '13px',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontWeight: 650,
              color: 'var(--text-main)'
            }}
          >
            <input
              type="checkbox"
              checked={selectedIds.size === candidates.length && candidates.length > 0}
              onChange={toggleSelectAll}
              style={{
                width: '18px',
                height: '18px',
                cursor: 'pointer',
                accentColor: 'var(--primary)'
              }}
            />
            <span>
              {selectedIds.size === candidates.length ? 'Deselect All' : `Select All (${candidates.length})`}
            </span>
          </label>

          {selectedIds.size > 0 && (
            <span
              style={{
                background: 'var(--primary-light)',
                color: 'var(--primary-dark)',
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 600
              }}
            >
              {selectedIds.size} PDF{selectedIds.size > 1 ? 's' : ''} selected
            </span>
          )}
        </div>

        {/* Action Buttons for Selection or Global */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {selectedIds.size > 0 ? (
            <>
              <button
                type="button"
                onClick={handleSaveSelectedNow}
                className="btn primary"
                disabled={loading}
                style={{
                  padding: '6px 14px',
                  fontSize: '12.5px',
                  fontWeight: 700,
                  background: 'var(--primary)',
                  color: '#FFFFFF'
                }}
              >
                <Check size={14} strokeWidth={2.5} />
                <span>Save Selected Now ({selectedIds.size})</span>
              </button>

              <button
                type="button"
                onClick={handleAcceptSelected}
                className="btn"
                style={{
                  padding: '6px 12px',
                  fontSize: '12.5px',
                  fontWeight: 650,
                  background: 'var(--primary-surface)',
                  color: 'var(--primary-dark)',
                  border: '1px solid var(--primary)'
                }}
              >
                <CheckCircle2 size={14} />
                <span>Mark to Keep ({selectedIds.size})</span>
              </button>

              <button
                type="button"
                onClick={handleRejectSelected}
                className="btn"
                style={{
                  padding: '6px 12px',
                  fontSize: '12.5px',
                  fontWeight: 650,
                  background: 'var(--s-fail-bg)',
                  color: 'var(--s-fail-text)',
                  border: '1px solid #FCA5A5'
                }}
              >
                <XCircle size={14} />
                <span>Mark to Reject ({selectedIds.size})</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  textDecoration: 'underline',
                  padding: '4px 6px'
                }}
              >
                Clear Selection
              </button>
            </>
          ) : (
            <>
              <span style={{ fontSize: '13px', color: 'var(--text-dim)', marginRight: '6px' }}>
                Summary: <strong style={{ color: 'var(--primary-dark)' }}>{totalWillBeSaved} to save</strong>,{' '}
                <strong style={{ color: '#DC2626' }}>{totalWillBeRejected} to reject</strong>
              </span>

              <button
                type="button"
                onClick={handleAcceptAll}
                className="btn"
                style={{
                  padding: '5px 11px',
                  fontSize: '12px',
                  fontWeight: 600,
                  background: 'var(--bg-card)',
                  color: 'var(--primary-dark)',
                  border: '1px solid var(--border-strong)'
                }}
              >
                Accept All ({candidates.length})
              </button>

              <button
                type="button"
                onClick={handleRejectAll}
                className="btn"
                style={{
                  padding: '5px 11px',
                  fontSize: '12px',
                  fontWeight: 600,
                  background: 'var(--bg-card)',
                  color: '#DC2626',
                  border: '1px solid var(--border-strong)'
                }}
              >
                Reject All ({candidates.length})
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div
          style={{
            background: '#FEE2E2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '12px 16px',
            borderRadius: '10px',
            fontSize: '13.5px'
          }}
        >
          {error}
        </div>
      )}

      {/* Group 1: Needs Your Decision (if any) */}
      {needsDecision.length > 0 && (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
          <div
            style={{
              background: 'var(--s-wait-bg)',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: 'var(--s-wait-text)',
                fontWeight: 650,
                fontSize: '14px'
              }}
            >
              <AlertTriangle size={18} />
              <span>Needs Your Decision ({needsDecision.length})</span>
            </div>
            {unresolvedNeedsReview.length > 0 && (
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--s-wait-text)',
                  background: 'rgba(0,0,0,0.1)',
                  padding: '2px 8px',
                  borderRadius: '4px'
                }}
              >
                {unresolvedNeedsReview.length} unresolved decision{unresolvedNeedsReview.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div>{needsDecision.map(renderCandidateRow)}</div>
        </div>
      )}

      {/* Group 2: Candidates Evaluated as "Keep" */}
      <div style={{ border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
        <div
          style={{
            background: 'var(--s-done-bg)',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            color: 'var(--s-done-text)',
            fontWeight: 650,
            fontSize: '14px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} />
            <span>Eligible Candidate Reports ({willBeSavedOriginal.length})</span>
          </div>
          <span style={{ fontSize: '12.5px', fontWeight: 600, opacity: 0.9 }}>
            Use the Accept/Reject buttons or checkboxes to customize what gets saved
          </span>
        </div>
        {willBeSavedOriginal.length === 0 ? (
          <div style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '13.5px', background: 'var(--bg-card)' }}>
            No automatic keep candidates.
          </div>
        ) : (
          <div>{willBeSavedOriginal.map(renderCandidateRow)}</div>
        )}
      </div>

      {/* Group 3: Duplicates */}
      {duplicates.length > 0 && (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
          <div
            style={{
              background: 'var(--bg-subtle)',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--text-muted)',
              fontWeight: 650,
              fontSize: '14px'
            }}
          >
            <Copy size={18} />
            <span>Duplicates ({duplicates.length}) — Default rejected</span>
          </div>
          <div>{duplicates.map(renderCandidateRow)}</div>
        </div>
      )}

      {/* Group 4: Excluded */}
      {excluded.length > 0 && (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
          <div
            style={{
              background: 'var(--s-wait-bg)',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--s-wait-text)',
              fontWeight: 650,
              fontSize: '14px'
            }}
          >
            <Ban size={18} />
            <span>Excluded (Different Patient / Date Out of Range) ({excluded.length})</span>
          </div>
          <div>{excluded.map(renderCandidateRow)}</div>
        </div>
      )}

      {/* Group 5: Rejected */}
      {rejected.length > 0 && (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: '12px', overflow: 'hidden' }}>
          <div
            style={{
              background: 'var(--s-fail-bg)',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--s-fail-text)',
              fontWeight: 650,
              fontSize: '14px'
            }}
          >
            <XCircle size={18} />
            <span>Rejected (Invalid PDF / Unreadable) ({rejected.length})</span>
          </div>
          <div>{rejected.map(renderCandidateRow)}</div>
        </div>
      )}

      {/* In-app PDF Viewer Modal */}
      <PdfModal
        isOpen={Boolean(activePdf)}
        pdfUrl={activePdf?.url || null}
        title={activePdf?.title}
        onClose={() => setActivePdf(null)}
      />
    </div>
  );
};
