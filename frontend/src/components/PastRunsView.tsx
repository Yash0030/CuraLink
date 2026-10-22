import React, { useEffect, useState } from 'react';
import { Trash2, CheckSquare, Square } from 'lucide-react';
import type { RunSummary } from '../types';
import { fetchAllRuns, deleteRun, deleteRuns } from '../api';
import { RunView } from './RunView';

export const PastRunsView: React.FC = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await fetchAllRuns();
      setRuns(data);
    } catch (err) {
      console.error('Failed to load past runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

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

  const getStatusMeta = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          label: 'Completed',
          cls: 's-done',
          icon: 'M5 12.5l4.5 4.5L19 7.5'
        };
      case 'waiting_approval':
        return {
          label: 'Waiting for approval',
          cls: 's-wait',
          icon: 'M12 8v5M12 16.5v.5'
        };
      case 'running':
      case 'checking':
        return {
          label: 'Checking records',
          cls: 's-work',
          icon: 'M12 3a9 9 0 1 0 9 9'
        };
      case 'failed':
        return {
          label: 'Failed',
          cls: 's-fail',
          icon: 'M18 6L6 18M6 6l12 12'
        };
      case 'cancelled':
      case 'rejected_by_human':
        return {
          label: 'Cancelled',
          cls: 's-fail',
          icon: 'M18 6L6 18M6 6l12 12'
        };
      case 'pending':
      default:
        return {
          label: 'Pending',
          cls: 's-pend',
          icon: 'M12 7v5l3 2'
        };
    }
  };

  const formatLabs = (labs: string[]) => {
    if (!labs || labs.length === 0) return 'None';
    return labs.map(l => {
      if (l === 'a1' || l === 'labA') return 'A1';
      if (l === 'cityscan' || l === 'labB') return 'CityScan';
      if (l === 'vitals' || l === 'labC') return 'Vitals';
      return l;
    }).join(', ');
  };

  const toggleSelect = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === runs.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(runs.map(r => r.id)));
    }
  };

  const handleDeleteSingle = async (runId: string, patientName: string) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete the collection run for "${patientName}"?\n\nThis will permanently delete the run, its staged candidates, and events.`
    );
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteRun(runId);
      setRuns(prev => prev.filter(r => r.id !== runId));
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(runId);
        return next;
      });
      if (selectedRunId === runId) {
        setSelectedRunId(null);
      }
    } catch (err: any) {
      console.error('Delete run error:', err);
      alert('Failed to delete run: ' + (err.message || String(err)));
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    const count = selectedIds.size;
    const confirmed = window.confirm(
      `Are you sure you want to delete ${count} selected collection run${count > 1 ? 's' : ''}?\n\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteRuns(Array.from(selectedIds));
      setRuns(prev => prev.filter(r => !selectedIds.has(r.id)));
      if (selectedRunId && selectedIds.has(selectedRunId)) {
        setSelectedRunId(null);
      }
      setSelectedIds(new Set());
    } catch (err: any) {
      console.error('Delete selected runs error:', err);
      alert('Failed to delete selected runs: ' + (err.message || String(err)));
    } finally {
      setDeleting(false);
    }
  };

  const handleClearAll = async () => {
    if (runs.length === 0) return;
    const confirmed = window.confirm(
      `Are you sure you want to delete ALL past collection runs (${runs.length})?\n\nAll historical collection data, staged candidates, and events will be permanently removed.`
    );
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteRuns();
      setRuns([]);
      setSelectedIds(new Set());
      setSelectedRunId(null);
    } catch (err: any) {
      console.error('Clear all runs error:', err);
      alert('Failed to clear runs: ' + (err.message || String(err)));
    } finally {
      setDeleting(false);
    }
  };

  if (selectedRunId) {
    const selectedRun = runs.find(r => r.id === selectedRunId);
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '14px',
          padding: '14px 20px'
        }}>
          <button
            type="button"
            onClick={() => setSelectedRunId(null)}
            className="btn"
            style={{ minHeight: '38px', padding: '0 16px', fontSize: '14px' }}
          >
            ← Back to Past runs
          </button>

          {selectedRun && (
            <div style={{ fontSize: '14.5px', color: 'var(--text-muted)' }}>
              Viewing Past Run: <strong style={{ color: 'var(--text-main)' }}>{selectedRun.patient_name}</strong>
              <span style={{ margin: '0 8px' }}>•</span>
              <span>{selectedRun.date_from} to {selectedRun.date_to}</span>
            </div>
          )}

          <button
            type="button"
            onClick={() => handleDeleteSingle(selectedRunId, selectedRun?.patient_name || 'this run')}
            disabled={deleting}
            className="btn danger"
            style={{
              minHeight: '38px',
              padding: '0 16px',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Trash2 size={16} />
            <span>{deleting ? 'Deleting...' : 'Delete this run'}</span>
          </button>
        </div>

        <RunView
          runId={selectedRunId}
          onRunCompleted={loadRuns}
          onCancelRun={() => setSelectedRunId(null)}
        />
      </div>
    );
  }

  return (
    <>
      <header style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '16px'
      }}>
        <div style={{ maxWidth: '560px' }}>
          <h1 style={{ margin: 0, fontSize: '30px', lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>
            Past runs
          </h1>
          <p style={{ margin: '8px 0 0', fontSize: '15px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
            A record of every collection, newest first.
          </p>
        </div>

        {/* Global Deletion & Selection Actions */}
        {runs.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {selectedIds.size > 0 ? (
              <>
                <button
                  type="button"
                  onClick={handleDeleteSelected}
                  disabled={deleting}
                  className="btn danger"
                  style={{ minHeight: '38px', padding: '0 16px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Trash2 size={16} />
                  <span>Delete Selected ({selectedIds.size})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set())}
                  className="btn"
                  style={{ minHeight: '38px', padding: '0 14px', fontSize: '14px' }}
                >
                  Deselect all
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={toggleSelectAll}
                  className="btn"
                  style={{ minHeight: '38px', padding: '0 14px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <CheckSquare size={16} />
                  <span>Select all</span>
                </button>
                <button
                  type="button"
                  onClick={handleClearAll}
                  disabled={deleting}
                  className="btn danger"
                  style={{ minHeight: '38px', padding: '0 14px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Trash2 size={16} />
                  <span>Clear all runs</span>
                </button>
              </>
            )}
          </div>
        )}
      </header>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <svg className="spin" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.4" strokeLinecap="round" style={{ margin: '0 auto 12px', display: 'block' }}>
            <path d="M12 3a9 9 0 1 0 9 9"></path>
          </svg>
          <p>Loading past runs history...</p>
        </div>
      ) : runs.length === 0 ? (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          padding: '48px 32px',
          textAlign: 'center'
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'var(--primary-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9"></circle>
              <path d="M12 7v5l3 2"></path>
            </svg>
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 8px', color: 'var(--text-main)' }}>
            No past runs found
          </h2>
          <p style={{ fontSize: '14.5px', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto' }}>
            Start a collection to search connected lab portals and retrieve patient reports.
          </p>
        </div>
      ) : (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '14px', overflow: 'hidden' }}>
          {runs.map(r => {
            const meta = getStatusMeta(r.status);
            const isSelected = selectedIds.has(r.id);

            return (
              <article
                key={r.id}
                className="row"
                style={{
                  background: isSelected ? 'var(--primary-light)' : undefined,
                  transition: 'background 0.15s ease'
                }}
              >
                {/* Selection Checkbox */}
                <button
                  type="button"
                  onClick={(e) => toggleSelect(r.id, e)}
                  title={isSelected ? 'Deselect run' : 'Select run'}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isSelected ? 'var(--primary-dark)' : 'var(--text-dim)'
                  }}
                >
                  {isSelected ? <CheckSquare size={20} color="var(--primary)" /> : <Square size={20} />}
                </button>

                <div style={{ flex: '1 1 190px', display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-start' }}>
                  <div style={{ fontSize: '17px', fontWeight: 650, color: 'var(--text-main)' }}>{r.patient_name}</div>
                  <span className={`status ${meta.cls}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d={meta.icon}></path>
                    </svg>
                    {meta.label}
                  </span>
                </div>

                <div style={{ flex: '1 1 110px' }}>
                  <div className="k">Patient ID</div>
                  <div className="v">{r.patient_id || 'pt001'}</div>
                </div>

                <div style={{ flex: '1 1 180px' }}>
                  <div className="k">Dates searched</div>
                  <div className="v">{r.date_from} to {r.date_to}</div>
                </div>

                <div style={{ flex: '1 1 190px' }}>
                  <div className="k">Labs</div>
                  <div className="v">{formatLabs(r.labs)}</div>
                </div>

                <div style={{ flex: '1 1 160px' }}>
                  <div className="k">Started</div>
                  <div className="v">{formatRunDate(r.created_at)}</div>
                </div>

                {/* Actions: View Details and Delete */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setSelectedRunId(r.id)}
                    className="btn"
                    style={{ minHeight: '38px', padding: '0 14px' }}
                  >
                    View details
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSingle(r.id, r.patient_name);
                    }}
                    disabled={deleting}
                    className="btn danger"
                    title="Delete run"
                    style={{
                      minHeight: '38px',
                      padding: '0 10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
};
