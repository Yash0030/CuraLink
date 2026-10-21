import React, { useEffect, useState } from 'react';
import { Calendar, Search, ShieldCheck, AlertCircle, ExternalLink, Activity } from 'lucide-react';
import type { TimelineReportItem } from '../types';
import { fetchTimeline, getPdfFileUrl } from '../api';

export const TimelineView: React.FC = () => {
  const [reports, setReports] = useState<TimelineReportItem[]>([]);
  const [patientFilter, setPatientFilter] = useState('');
  const [loading, setLoading] = useState(true);

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

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '28px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px' }}>Personal Health Timeline</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Chronological, deduplicated medical record consolidated across all lab portals.
          </p>
        </div>

        {/* Patient Key Filter */}
        <form onSubmit={handleFilterSubmit} style={{ display: 'flex', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              className="input-field"
              placeholder="Filter by patient key / name..."
              value={patientFilter}
              onChange={e => setPatientFilter(e.target.value)}
              style={{ paddingLeft: '34px', width: '260px' }}
            />
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-dim)' }} />
          </div>
          <button type="submit" className="btn btn-secondary">
            Filter
          </button>
        </form>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <Activity size={28} color="#6366f1" style={{ animation: 'spin 1.5s linear infinite', margin: '0 auto 12px' }} />
          <p>Loading medical timeline...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-dim)' }}>
          <Calendar size={40} style={{ margin: '0 auto 16px', opacity: 0.4 }} />
          <h3 style={{ fontSize: '16px', color: '#fff', marginBottom: '6px' }}>No Health Records Stored Yet</h3>
          <p style={{ fontSize: '13px', maxWidth: '400px', margin: '0 auto' }}>
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
            background: 'linear-gradient(180deg, #6366f1 0%, #14b8a6 50%, rgba(255,255,255,0.05) 100%)'
          }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {reports.map((item) => {
              const pdfUrl = item.candidate_id ? getPdfFileUrl(item.candidate_id) : '#';
              const labDisplay = item.lab === 'labA' ? 'A1 Diagnostics' : item.lab === 'labB' ? 'CityScan Imaging' : item.lab === 'labC' ? 'Vitals Laboratory' : item.lab;

              return (
                <div key={item.report_uuid} style={{ position: 'relative' }}>
                  {/* Timeline node dot */}
                  <div style={{
                    position: 'absolute',
                    left: '-32px',
                    top: '18px',
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: '#090d16',
                    border: '3px solid #6366f1',
                    boxShadow: '0 0 10px rgba(99, 102, 241, 0.4)'
                  }} />

                  {/* Card */}
                  <div className="glass-panel" style={{ padding: '18px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '4px',
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#818cf8',
                          textTransform: 'uppercase'
                        }}>
                          {labDisplay}
                        </span>
                        <h3 style={{ fontSize: '16px', margin: 0, color: '#fff' }}>
                          {item.test_name}
                        </h3>
                      </div>

                      {/* Re-check Badge */}
                      <div>
                        {item.recheck_ok === true ? (
                          <span className="badge badge-keep" title={item.recheck_note || 'Re-check confirmed name & date'}>
                            <ShieldCheck size={14} />
                            <span>Re-Check Verified</span>
                          </span>
                        ) : item.recheck_ok === false ? (
                          <span className="badge badge-reject" title={item.recheck_note || 'Re-check failed'}>
                            <AlertCircle size={14} />
                            <span>Re-Check Discrepancy</span>
                          </span>
                        ) : (
                          <span className="badge badge-pending">
                            Stored
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '12px' }}>
                      <span style={{ color: '#cbd5e1' }}><strong>Date:</strong> {item.report_date}</span>
                      <span><strong>Report ID:</strong> {item.report_id}</span>
                      <span><strong>Patient:</strong> {item.x_name || item.patient_key}</span>
                      <span><strong>SHA-256:</strong> <code>{item.sha256?.substring(0, 10)}...</code></span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                        Indexed: {new Date(item.created_at).toLocaleString()}
                      </span>

                      {item.candidate_id && (
                        <a
                          href={pdfUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-secondary"
                          style={{ padding: '6px 14px', fontSize: '12px' }}
                        >
                          <span>Open PDF Document</span>
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
