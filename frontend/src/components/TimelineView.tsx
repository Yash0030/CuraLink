import React, { useEffect, useState } from 'react';
import { Search, ShieldCheck, AlertCircle, FileText, Trash2, CheckSquare, Square, ExternalLink } from 'lucide-react';
import type { TimelineReportItem } from '../types';
import { fetchTimeline, getPdfFileUrl, deleteTimelineReport, deleteTimelineReports } from '../api';
import { PdfModal } from './PdfModal';
import { useConfirm } from './ConfirmModal';

export const TimelineView: React.FC = () => {
  const [reports, setReports] = useState<TimelineReportItem[]>([]);
  const [patientFilter, setPatientFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [activePdf, setActivePdf] = useState<{ url: string; title: string } | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const { confirm, showAlert } = useConfirm();

  const loadTimeline = async (filterKey?: string) => {
    setLoading(true);
    try {
      const data = await fetchTimeline(filterKey);
      setReports(data);
    } catch (err) {
      console.error('Failed to load timeline:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, []);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadTimeline(patientFilter.trim() || undefined);
  };

  const openPdf = (item: TimelineReportItem) => {
    const fileId = item.candidate_id || item.report_uuid;
    setActivePdf({
      url: getPdfFileUrl(fileId),
      title: `${item.test_name} (${item.report_date})`
    });
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
    if (selectedIds.size === reports.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(reports.map(r => r.report_uuid)));
    }
  };

  const handleDeleteSingle = async (reportId: string, testName: string) => {
    const confirmed = await confirm({
      title: 'Delete Health Record',
      message: `Are you sure you want to delete the record for "${testName}" from the timeline?\n\nThis will remove it from the patient timeline.`,
      confirmText: 'Delete Record',
      cancelText: 'Cancel',
      isDanger: true,
    });
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteTimelineReport(reportId);
      setReports(prev => prev.filter(r => r.report_uuid !== reportId));
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(reportId);
        return next;
      });
    } catch (err: any) {
      console.error('Delete timeline report error:', err);
      await showAlert('Failed to Delete Record', err.message || String(err));
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    const count = selectedIds.size;
    const confirmed = await confirm({
      title: `Delete ${count} Selected Record${count > 1 ? 's' : ''}`,
      message: `Are you sure you want to delete ${count} selected health record${count > 1 ? 's' : ''} from the timeline?\n\nThis action cannot be undone.`,
      confirmText: `Delete ${count} Record${count > 1 ? 's' : ''}`,
      cancelText: 'Cancel',
      isDanger: true,
    });
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteTimelineReports(Array.from(selectedIds));
      setReports(prev => prev.filter(r => !selectedIds.has(r.report_uuid)));
      setSelectedIds(new Set());
    } catch (err: any) {
      console.error('Delete selected records error:', err);
      await showAlert('Failed to Delete Records', err.message || String(err));
    } finally {
      setDeleting(false);
    }
  };

  const handleClearAll = async () => {
    if (reports.length === 0) return;
    const confirmed = await confirm({
      title: 'Clear All Health Records',
      message: `Are you sure you want to delete ALL health records (${reports.length}) from the timeline?\n\nAll verified clinical reports will be removed.`,
      confirmText: 'Clear All Records',
      cancelText: 'Cancel',
      isDanger: true,
    });
    if (!confirmed) return;

    try {
      setDeleting(true);
      await deleteTimelineReports();
      setReports([]);
      setSelectedIds(new Set());
    } catch (err: any) {
      console.error('Clear timeline error:', err);
      await showAlert('Failed to Clear Records', err.message || String(err));
    } finally {
      setDeleting(false);
    }
  };

  const getLabChipCls = (lab: string) => {
    if (lab === 'labA' || lab.toLowerCase().includes('a1')) return 'lab-a1';
    if (lab === 'labB' || lab.toLowerCase().includes('cityscan')) return 'lab-cs';
    if (lab === 'labC' || lab.toLowerCase().includes('vitals')) return 'lab-vt';
    return 'lab-custom';
  };

  const getLabName = (lab: string) => {
    if (lab === 'labA') return 'A1 Diagnostics';
    if (lab === 'labB') return 'CityScan Imaging';
    if (lab === 'labC') return 'Vitals Laboratory';
    return lab;
  };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <header style={{ maxWidth: '540px' }}>
          <h1 style={{ margin: 0, fontSize: '30px', lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.01em' }}>
            Health timeline
          </h1>
          <p style={{ margin: '8px 0 0', fontSize: '15px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
            Chronological, deduplicated medical record consolidated across all lab portals.
          </p>
        </header>

        {/* Action Controls: Search & Deletion Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Patient Key Filter */}
          <form onSubmit={handleFilterSubmit} style={{ display: 'flex', gap: '8px' }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Filter by patient name..."
                value={patientFilter}
                onChange={e => setPatientFilter(e.target.value)}
                style={{
                  width: '240px',
                  minHeight: '40px',
                  padding: '0 14px 0 36px',
                  borderRadius: '10px',
                  border: '1px solid var(--border-input)',
                  font: '400 14px Onest, sans-serif',
                  color: 'var(--text-main)',
                  background: 'var(--bg-input)'
                }}
              />
              <Search size={15} style={{ position: 'absolute', left: '12px', top: '13px', color: 'var(--text-dim)' }} />
            </div>
            <button type="submit" className="btn" style={{ minHeight: '40px', padding: '0 14px' }}>
              Filter
            </button>
          </form>

          {/* Deletion & Batch Action Buttons */}
          {reports.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {selectedIds.size > 0 ? (
                <>
                  <button
                    type="button"
                    onClick={handleDeleteSelected}
                    disabled={deleting}
                    className="btn danger"
                    style={{ minHeight: '40px', padding: '0 14px', fontSize: '13.5px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Trash2 size={15} />
                    <span>Delete Selected ({selectedIds.size})</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedIds(new Set())}
                    className="btn"
                    style={{ minHeight: '40px', padding: '0 12px', fontSize: '13.5px' }}
                  >
                    Deselect
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={toggleSelectAll}
                    className="btn"
                    style={{ minHeight: '40px', padding: '0 12px', fontSize: '13.5px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <CheckSquare size={15} />
                    <span>Select all</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleClearAll}
                    disabled={deleting}
                    className="btn danger"
                    style={{ minHeight: '40px', padding: '0 12px', fontSize: '13.5px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Trash2 size={15} />
                    <span>Clear all</span>
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <svg className="spin" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2.4" strokeLinecap="round" style={{ margin: '0 auto 12px', display: 'block' }}>
            <path d="M12 3a9 9 0 1 0 9 9"></path>
          </svg>
          <p>Loading medical timeline...</p>
        </div>
      ) : reports.length === 0 ? (
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
            <FileText size={26} color="var(--primary)" />
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 8px', color: 'var(--text-main)' }}>
            No health records stored yet
          </h2>
          <p style={{ fontSize: '14.5px', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto' }}>
            Run a collection across lab portals to automatically fetch, verify, deduplicate, and assemble the patient timeline.
          </p>
        </div>
      ) : (
        <div style={{ position: 'relative', paddingLeft: '32px' }}>
          {/* Vertical timeline spine line */}
          <div style={{
            position: 'absolute',
            left: '11px',
            top: '16px',
            bottom: '16px',
            width: '2px',
            background: 'var(--border-strong)'
          }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {reports.map((item) => {
              const labDisplay = getLabName(item.lab);
              const chipClass = getLabChipCls(item.lab);
              const isSelected = selectedIds.has(item.report_uuid);

              return (
                <div key={item.report_uuid} style={{ position: 'relative' }}>
                  {/* Timeline node dot */}
                  <div style={{
                    position: 'absolute',
                    left: '-32px',
                    top: '20px',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    background: 'var(--primary)',
                    border: '3px solid var(--primary-light)'
                  }} />

                  {/* Card */}
                  <div style={{
                    background: isSelected ? 'var(--primary-light)' : 'var(--bg-card)',
                    border: isSelected ? '1.5px solid var(--primary)' : '1px solid var(--border-color)',
                    borderRadius: '14px',
                    padding: '20px 24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '14px',
                    transition: 'all 0.15s ease',
                    boxShadow: isSelected ? '0 4px 14px rgba(11, 122, 117, 0.12)' : 'none'
                  }}>
                    {/* Top Row: Checkbox, Lab, Title, Verification Badge, and Delete Button */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {/* Selection Checkbox */}
                        <button
                          type="button"
                          onClick={(e) => toggleSelect(item.report_uuid, e)}
                          title={isSelected ? 'Deselect record' : 'Select record'}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '2px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: isSelected ? 'var(--primary)' : 'var(--text-dim)'
                          }}
                        >
                          {isSelected ? <CheckSquare size={20} color="var(--primary)" /> : <Square size={20} />}
                        </button>

                        <span className={`chip ${chipClass}`}>
                          {labDisplay}
                        </span>

                        {/* Interactive Clickable Test Name */}
                        <button
                          type="button"
                          onClick={() => openPdf(item)}
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            cursor: 'pointer',
                            fontSize: '17px',
                            fontWeight: 650,
                            color: 'var(--text-main)',
                            textAlign: 'left',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            textDecoration: 'none'
                          }}
                          className="hover-underline"
                          title="Click to view PDF document in reader"
                        >
                          <span>{item.test_name}</span>
                          <ExternalLink size={14} color="var(--primary)" />
                        </button>
                      </div>

                      {/* Right Action: Re-check Badge and Delete Action */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {item.recheck_ok === true ? (
                          <span className="status s-done" title={item.recheck_note || 'Re-check confirmed name & date'}>
                            <ShieldCheck size={14} />
                            <span>Verified</span>
                          </span>
                        ) : item.recheck_ok === false ? (
                          <span className="status s-fail" title={item.recheck_note || 'Re-check failed'}>
                            <AlertCircle size={14} />
                            <span>Discrepancy</span>
                          </span>
                        ) : (
                          <span className="status s-done">
                            <ShieldCheck size={14} />
                            <span>Verified</span>
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={() => handleDeleteSingle(item.report_uuid, item.test_name)}
                          disabled={deleting}
                          className="btn danger"
                          style={{ minHeight: '32px', padding: '0 8px', fontSize: '12px' }}
                          title="Delete this health record"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Metadata Details Row */}
                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: '16px 28px',
                      fontSize: '13.5px'
                    }}>
                      <div><span className="k">Date:</span> <strong className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.report_date}</strong></div>
                      <div><span className="k">Report ID:</span> <span className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.report_id}</span></div>
                      <div><span className="k">Patient:</span> <span className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.x_name || item.patient_key}</span></div>
                      
                      {/* Interactive Clickable PDF Filename Badge */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="k">PDF File:</span>
                        <button
                          type="button"
                          onClick={() => openPdf(item)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            background: 'var(--bg-subtle)',
                            border: '1px solid var(--border-color)',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            color: 'var(--primary)',
                            fontWeight: 600,
                            cursor: 'pointer',
                            fontFamily: 'var(--font-mono, monospace)'
                          }}
                          title="Click to open in PDF reader"
                        >
                          <FileText size={12} />
                          <span>{item.filename || `${item.report_id}.pdf`}</span>
                        </button>
                      </div>

                      <div><span className="k">SHA-256:</span> <code style={{ color: 'var(--text-dim)' }}>{item.sha256?.substring(0, 10)}...</code></div>
                    </div>

                    {/* Card Footer: Timestamp and Launch Viewer Button */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px', marginTop: '2px' }}>
                      <span style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
                        Indexed: {new Date(item.created_at).toLocaleString()}
                      </span>

                      <button
                        type="button"
                        onClick={() => openPdf(item)}
                        className="btn primary"
                        style={{ minHeight: '34px', padding: '0 14px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <FileText size={14} />
                        <span>View PDF Document</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
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
