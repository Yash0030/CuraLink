import { useEffect, useState } from 'react';
import { Banner } from './components/Banner';
import { Navbar } from './components/Navbar';
import { NewCollectionModal } from './components/NewCollectionModal';
import { RunView } from './components/RunView';
import { TimelineView } from './components/TimelineView';
import { PastRunsView } from './components/PastRunsView';
import type { LabInfo } from './types';
import { fetchLabs, createNewRun } from './api';
import { Activity, Plus, FileText } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<'current' | 'history' | 'timeline'>('current');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [labs, setLabs] = useState<LabInfo[]>([]);

  useEffect(() => {
    fetchLabs()
      .then(setLabs)
      .catch(err => {
        console.error('Failed to load lab configs:', err);
        // Fallback default definitions if server starting
        setLabs([
          { key: 'labA', name: 'A1', layout: 'table', has_captcha: false, reports_path: '/labA/reports' },
          { key: 'labB', name: 'CityScan Imaging', layout: 'cards', has_captcha: true, reports_path: '/labB/reports' },
          { key: 'labC', name: 'Vitals', layout: 'paginated', has_captcha: true, reports_path: '/labC/reports' },
        ]);
      });
  }, []);

  const handleStartRun = async (data: any) => {
    const res = await createNewRun(data);
    setCurrentRunId(res.run_id);
    setActiveTab('current');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Synthetic Data & CAPTCHA Safety Banner */}
      <Banner />

      {/* Main Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenNewCollection={() => setIsModalOpen(true)}
        hasActiveRun={Boolean(currentRunId)}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1 }}>
        {activeTab === 'current' && (
          currentRunId ? (
            <RunView
              runId={currentRunId}
              onRunCompleted={() => {
                // Keep view active
              }}
            />
          ) : (
            <div style={{ maxWidth: '800px', margin: '80px auto', padding: '0 24px', textAlign: 'center' }}>
              <div className="glass-panel" style={{ padding: '48px 32px' }}>
                <div style={{
                  background: 'rgba(99, 102, 241, 0.12)',
                  width: '64px',
                  height: '64px',
                  borderRadius: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 20px'
                }}>
                  <Activity size={32} color="#818cf8" />
                </div>
                <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>Personal Health Record Organizer</h2>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '520px', margin: '0 auto 28px' }}>
                  A patient has diagnostic reports spread across three lab portals (A1, CityScan Imaging, and Vitals).
                  The app logs into each portal, collects reports in the date range, eliminates duplicates and look-alikes,
                  and saves an authenticated health timeline.
                </p>

                <div style={{ display: 'flex', justifyContent: 'center', gap: '14px' }}>
                  <button onClick={() => setIsModalOpen(true)} className="btn btn-primary" style={{ padding: '12px 24px', fontSize: '15px' }}>
                    <Plus size={18} />
                    <span>Start New Collection</span>
                  </button>
                  <button onClick={() => setActiveTab('timeline')} className="btn btn-secondary" style={{ padding: '12px 24px', fontSize: '15px' }}>
                    <FileText size={18} />
                    <span>View Stored Timeline</span>
                  </button>
                </div>
              </div>
            </div>
          )
        )}

        {activeTab === 'timeline' && <TimelineView />}

        {activeTab === 'history' && (
          <PastRunsView
            onSelectRun={(id) => {
              setCurrentRunId(id);
              setActiveTab('current');
            }}
          />
        )}
      </main>

      {/* New Collection Modal */}
      <NewCollectionModal
        labs={labs}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleStartRun}
      />
    </div>
  );
}

export default App;
