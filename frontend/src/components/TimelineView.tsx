import React, { useEffect, useState } from 'react';
import { Search, ShieldCheck, AlertCircle, FileText } from 'lucide-react';
import type { TimelineReportItem } from '../types';
import { fetchTimeline, getPdfFileUrl } from '../api';
import { PdfModal } from './PdfModal';

export const TimelineView: React.FC = () => {
  const [reports, setReports] = useState<TimelineReportItem[]>([]);
  const [patientFilter, setPatientFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [activePdf, setActivePdf] = useState<{ url: string; title: string } | null>(null);

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
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <header style={{ maxWidth: '560px' }}>
          <h1 style={{ margin: 0, fontSize: '30px', lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.01em' }}>
            Health timeline
          </h1>
          <p style={{ margin: '8px 0 0', fontSize: '15px', lineHeight: 1.5, color: '#3A4A5E' }}>
            Chronological, deduplicated medical record consolidated across all lab portals.
          </p>
        </header>

        {/* Patient Key Filter */}
        <form onSubmit={handleFilterSubmit} style={{ display: 'flex', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Filter by patient name / key..."
              value={patientFilter}
              onChange={e => setPatientFilter(e.target.value)}
              style={{
                width: '260px',
                minHeight: '44px',
                padding: '0 14px 0 38px',
                borderRadius: '10px',
                border: '1px solid var(--border-input)',
                font: '400 14.5px Onest, sans-serif',
                color: 'var(--text-main)',
                background: 'var(--bg-input)'
              }}
            />
            <Search size={16} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--text-dim)' }} />
          </div>
          <button type="submit" className="btn">
            Filter
          </button>
        </form>
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
              const pdfUrl = item.candidate_id ? getPdfFileUrl(item.candidate_id) : '#';
              const labDisplay = getLabName(item.lab);
              const chipClass = getLabChipCls(item.lab);

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
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '14px',
                    padding: '20px 24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className={`chip ${chipClass}`}>
                          {labDisplay}
                        </span>
                        <h3 style={{ fontSize: '17px', margin: 0, fontWeight: 650, color: 'var(--text-main)' }}>
                          {item.test_name}
                        </h3>
                      </div>

                      {/* Re-check Badge */}
                      <div>
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
                          <span className="status s-pend">
                            Stored
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '16px 28px',
                      fontSize: '13.5px'
                    }}>
                      <div><span className="k">Date:</span> <strong className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.report_date}</strong></div>
                      <div><span className="k">Report ID:</span> <span className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.report_id}</span></div>
                      <div><span className="k">Patient:</span> <span className="v" style={{ display: 'inline', color: 'var(--text-main)' }}>{item.x_name || item.patient_key}</span></div>
                      <div><span className="k">SHA-256:</span> <code style={{ color: 'var(--text-dim)' }}>{item.sha256?.substring(0, 10)}...</code></div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px', marginTop: '4px' }}>
                      <span style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
                        Indexed: {new Date(item.created_at).toLocaleString()}
                      </span>

                      {item.candidate_id && (
                        <button
                          type="button"
                          onClick={() => setActivePdf({
                            url: pdfUrl,
                            title: `${item.test_name} - ${item.report_date}`
                          })}
                          className="btn"
                          style={{ minHeight: '34px', padding: '0 12px', fontSize: '13px' }}
                        >
                          <FileText size={14} />
                          <span>View PDF Document</span>
                        </button>
                      )}
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
