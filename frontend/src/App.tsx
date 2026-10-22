import { useEffect, useState, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { NewCollectionModal } from './components/NewCollectionModal';
import { ManageLabsModal } from './components/ManageLabsModal';
import { AuthModal } from './components/AuthModal';
import { RunView } from './components/RunView';
import { TimelineView } from './components/TimelineView';
import { PastRunsView } from './components/PastRunsView';
import type { LabInfo, UserProfile, RunSummary } from './types';
import { fetchLabs, createNewRun, fetchCurrentUser, logout, fetchAllRuns } from './api';
import { ShieldCheck, Lock, Sun, Moon } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<'current' | 'history' | 'timeline'>('current');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLabsModalOpen, setIsLabsModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [labs, setLabs] = useState<LabInfo[]>([]);
  const [allRuns, setAllRuns] = useState<RunSummary[]>([]);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // Theme Management (Light / Dark)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('phr_theme');
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('phr_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const refreshLabs = useCallback(async () => {
    try {
      const data = await fetchLabs();
      setLabs(data);
    } catch (err) {
      console.error('Failed to load lab configs:', err);
    }
  }, []);

  const refreshRuns = useCallback(async () => {
    try {
      const data = await fetchAllRuns();
      setAllRuns(data);
    } catch (err) {
      // Runs fetch might fail if not authenticated
    }
  }, []);

  useEffect(() => {
    // Check initial user authentication
    fetchCurrentUser()
      .then(user => {
        setCurrentUser(user);
        if (!user) {
          setIsAuthModalOpen(true);
        } else {
          refreshRuns();
        }
      })
      .catch(err => {
        console.warn('Auth check error:', err);
        setIsAuthModalOpen(true);
      })
      .finally(() => {
        setIsCheckingAuth(false);
        refreshLabs();
      });
  }, [refreshLabs, refreshRuns]);

  const handleStartRun = async (data: any) => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    const res = await createNewRun(data);
    setCurrentRunId(res.run_id);
    setActiveTab('current');
    refreshRuns();
  };

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setCurrentRunId(null);
    setAllRuns([]);
    setIsAuthModalOpen(true);
    refreshLabs();
  };

  const handleAuthSuccess = (user: UserProfile) => {
    setCurrentUser(user);
    setIsAuthModalOpen(false);
    refreshLabs();
    refreshRuns();
  };

  const lastRun = allRuns.length > 0 ? allRuns[0] : null;

  const formatRunDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: 'var(--bg-page)',
      fontFamily: "'Onest', system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      color: 'var(--text-main)',
      transition: 'background-color 0.2s ease, color 0.2s ease'
    }}>
      {/* Left Sidebar Navigation */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenNewCollection={() => {
          if (!currentUser) {
            setIsAuthModalOpen(true);
          } else {
            setIsModalOpen(true);
          }
        }}
        onOpenManageLabs={() => {
          if (!currentUser) {
            setIsAuthModalOpen(true);
          } else {
            setIsLabsModalOpen(true);
          }
        }}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        currentUser={currentUser}
        hasActiveRun={Boolean(currentRunId)}
      />

      {/* Main Content Area */}
      <main style={{
        flex: '1 1 auto',
        minWidth: 0,
        boxSizing: 'border-box',
        padding: '24px clamp(20px, 4vw, 56px) 40px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative'
      }}>
        {/* Top Header Bar with Theme Mode Selection (Top Right) */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', width: '100%' }}>
          <button
            type="button"
            onClick={toggleTheme}
            className="btn"
            style={{
              borderRadius: '24px',
              padding: '6px 14px',
              minHeight: '36px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '13px',
              fontWeight: 650,
              background: 'var(--bg-card)',
              color: 'var(--text-main)',
              border: '1px solid var(--border-strong)',
              boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer'
            }}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun size={15} color="#FDE047" /> : <Moon size={15} color="#0B7A75" />}
            <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
          </button>
        </div>
        {/* If user is not authenticated and modal is closed, show attractive gate banner */}
        {!currentUser && !isCheckingAuth ? (
          <div style={{ maxWidth: '680px', margin: '60px auto', width: '100%', textAlign: 'center' }}>
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              padding: '48px 36px',
              boxShadow: 'var(--shadow-md)'
            }}>
              <div style={{
                background: 'var(--primary-light)',
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px'
              }}>
                <Lock size={30} color="var(--primary)" />
              </div>

              <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '10px', color: 'var(--text-main)' }}>
                Sign in to Health Record Organizer
              </h2>
              <p style={{ fontSize: '15px', color: 'var(--text-muted)', maxWidth: '480px', margin: '0 auto 24px', lineHeight: 1.6 }}>
                Every patient has an isolated database session and private record repository.
                Please sign in or create an account to start orchestrating multi-agent record collection.
              </p>

              <button
                onClick={() => setIsAuthModalOpen(true)}
                className="btn primary"
                style={{ padding: '0 28px', minHeight: '46px', fontSize: '15px' }}
              >
                <ShieldCheck size={18} />
                <span>Sign In / Create Account</span>
              </button>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'current' && (
              currentRunId ? (
                <RunView
                  runId={currentRunId}
                  onRunCompleted={() => {
                    refreshRuns();
                  }}
                  onCancelRun={() => {
                    setCurrentRunId(null);
                    refreshRuns();
                  }}
                />
              ) : (
                /* Matches A_ActiveEmpty.dc.html exactly */
                <>
                  <header style={{ maxWidth: '560px' }}>
                    <h1 style={{ margin: 0, fontSize: '30px', lineHeight: 1.15, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-main)' }}>
                      Active run
                    </h1>
                    <p style={{ margin: '8px 0 0', fontSize: '15px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
                      Watch your assistant collect reports from each lab as it works.
                    </p>
                  </header>

                  <section style={{
                    maxWidth: '720px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '16px',
                    padding: '40px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: '20px'
                  }}>
                    <div style={{
                      width: '56px',
                      height: '56px',
                      borderRadius: '16px',
                      background: 'var(--primary-light)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M3 12h4l3-7 4 14 3-7h4"></path>
                      </svg>
                    </div>
                    <div>
                      <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 700, color: 'var(--text-main)' }}>No collection is running</h2>
                      <p style={{ margin: '8px 0 0', fontSize: '15.5px', lineHeight: 1.6, color: 'var(--text-muted)', maxWidth: '520px' }}>
                        Choose a patient, a date range and the labs to search. Your assistant signs in to each portal, downloads the reports and adds the new ones to your timeline.
                      </p>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                      <button
                        type="button"
                        onClick={() => setIsModalOpen(true)}
                        className="btn primary"
                      >
                        Start new collection
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveTab('timeline')}
                        className="btn"
                      >
                        View health timeline
                      </button>
                    </div>
                  </section>

                  <section style={{ maxWidth: '720px', display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
                    {/* Last run card */}
                    <div style={{
                      flex: '1 1 300px',
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '14px',
                      padding: '20px 24px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}>
                      <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-muted)' }}>Last run</h2>
                      {lastRun ? (
                        <>
                          <div style={{ fontSize: '17px', fontWeight: 650, color: 'var(--text-main)' }}>
                            {lastRun.patient_name}, {lastRun.status.replace(/_/g, ' ')}
                          </div>
                          <div style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                            {formatRunDate(lastRun.created_at)}<br />
                            {lastRun.date_from} to {lastRun.date_to}
                          </div>
                        </>
                      ) : (
                        <>
                          <div style={{ fontSize: '17px', fontWeight: 650, color: 'var(--text-main)' }}>No previous runs</div>
                          <div style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                            Start a collection to retrieve and consolidate reports from connected labs.
                          </div>
                        </>
                      )}
                    </div>

                    {/* Connected labs card */}
                    <div style={{
                      flex: '1 1 300px',
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '14px',
                      padding: '20px 24px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}>
                      <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-muted)' }}>Connected labs</h2>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {labs.map(lab => {
                          const chipCls = lab.key === 'a1' || lab.key === 'labA' ? 'lab-a1' : lab.key === 'cityscan' || lab.key === 'labB' ? 'lab-cs' : lab.key === 'vitals' || lab.key === 'labC' ? 'lab-vt' : 'lab-custom';
                          return (
                            <span key={lab.key} className={`chip ${chipCls}`}>
                              {lab.name}
                            </span>
                          );
                        })}
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsLabsModalOpen(true)}
                        style={{
                          border: 'none',
                          background: 'none',
                          padding: 0,
                          cursor: 'pointer',
                          textAlign: 'left',
                          fontSize: '14px',
                          fontWeight: 600,
                          color: 'var(--primary)'
                        }}
                      >
                        Manage labs
                      </button>
                    </div>
                  </section>
                </>
              )
            )}

            {activeTab === 'timeline' && <TimelineView />}

            {activeTab === 'history' && <PastRunsView />}
          </>
        )}
      </main>

      {/* New Collection Modal */}
      <NewCollectionModal
        labs={labs}
        isOpen={isModalOpen}
        currentUser={currentUser}
        onClose={() => setIsModalOpen(false)}
        onOpenManageLabs={() => {
          setIsModalOpen(false);
          setIsLabsModalOpen(true);
        }}
        onSubmit={handleStartRun}
      />

      {/* Manage Labs Modal */}
      <ManageLabsModal
        labs={labs}
        isOpen={isLabsModalOpen}
        onClose={() => setIsLabsModalOpen(false)}
        onLabsUpdated={refreshLabs}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
        canDismiss={Boolean(currentUser)}
      />
    </div>
  );
}

export default App;
