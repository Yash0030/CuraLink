import React from 'react';
import { X, Download, FileText } from 'lucide-react';

interface PdfModalProps {
  isOpen: boolean;
  pdfUrl: string | null;
  title?: string;
  onClose: () => void;
}

export const PdfModal: React.FC<PdfModalProps> = ({ isOpen, pdfUrl, title, onClose }) => {
  if (!isOpen || !pdfUrl) return null;

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1200 }}>
      <div
        className="modal-content"
        onClick={e => e.stopPropagation()}
        style={{
          maxWidth: '920px',
          width: '95vw',
          height: '88vh',
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          background: 'var(--bg-card-solid)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8)'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.03)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#818cf8',
              padding: '6px',
              borderRadius: '8px'
            }}>
              <FileText size={18} />
            </div>
            <div>
              <span style={{ fontSize: '15px', fontWeight: 600, color: '#fff', display: 'block' }}>
                {title || 'Diagnostic Report PDF'}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                In-App Document Viewer
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a
              href={pdfUrl}
              download
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px', gap: '6px' }}
            >
              <Download size={13} />
              <span>Download PDF</span>
            </a>
            <button
              onClick={onClose}
              type="button"
              style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}
              title="Close PDF Preview"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Embedded PDF iframe */}
        <div style={{ flex: 1, background: '#0b1120', overflow: 'hidden', position: 'relative' }}>
          <iframe
            src={pdfUrl}
            title={title || 'Diagnostic Report Document'}
            style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }}
          />
        </div>
      </div>
    </div>
  );
};
