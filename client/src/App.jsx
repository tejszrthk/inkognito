import React, { useState, useEffect } from 'react';
import { ShieldCheck, User, LogOut, ChevronLeft, LayoutDashboard } from 'lucide-react';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import IntakeForm from './components/IntakeForm';
import Pipeline from './components/Pipeline';
import Report from './components/Report';
import { api } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('inkognito_token'));
  const [view, setView] = useState('auth'); // auth, dashboard, intake, pipeline, report
  const [currentJobId, setCurrentJobId] = useState('');
  const [currentReport, setCurrentReport] = useState(null);
  const [currentSubject, setCurrentSubject] = useState(null);
  const [runError, setRunError] = useState('');

  // Auto-login if token exists
  useEffect(() => {
    if (token) {
      api.getCurrentUser()
        .then(userData => {
          setUser(userData);
          setView('dashboard');
        })
        .catch(() => {
          handleLogout();
        });
    }
  }, []);

  const handleLogin = (newToken, userData) => {
    setToken(newToken);
    setUser(userData);
    setView('dashboard');
  };

  const handleLogout = () => {
    api.logout();
    setToken(null);
    setUser(null);
    setView('auth');
  };

  const handleStartRun = async (formData) => {
    try {
      setRunError('');
      setCurrentSubject(formData);
      const data = await api.runVerification(formData);
      setCurrentJobId(data.job_id);
      setView('pipeline');
    } catch (err) {
      setRunError(err.message);
    }
  };

  const handleJobComplete = (jobData) => {
    setCurrentReport(jobData.report);
    setView('report');
  };

  const handleViewHistoricalReport = async (reportMetadata) => {
    try {
      const data = await api.getHistoricalReport(reportMetadata.report_id);
      setCurrentSubject({ name: reportMetadata.subject_name, city: 'Archived Record' });
      setCurrentReport(data.report);
      setView('report');
    } catch (err) {
      alert("Error loading report: " + err.message);
    }
  };

  return (
    <div className="app-container">
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '48px',
        padding: '0 8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', cursor: 'pointer' }} onClick={() => user && setView('dashboard')}>
          <div style={{ background: 'var(--accent-gold)', padding: '10px', borderRadius: '12px', display: 'flex' }}>
            <ShieldCheck size={28} color="#000" />
          </div>
          <div>
            <h1 className="serif-heading" style={{ fontSize: '1.6rem', letterSpacing: '0.05em', color: 'var(--accent-gold)' }}>INKOGNITO v2</h1>
            <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.2em' }}>Premium Verification Service</p>
          </div>
        </div>

        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--bg-panel)', padding: '8px 16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <User size={16} color="var(--accent-gold)" />
              <span style={{ fontSize: '0.9rem', fontWeight: '600' }}>{user.username}</span>
            </div>
            
            {view !== 'dashboard' && view !== 'auth' && (
              <button className="btn btn-outline" style={{ padding: '8px 16px', fontSize: '0.8rem' }} onClick={() => setView('dashboard')}>
                <LayoutDashboard size={16} />
                Dashboard
              </button>
            )}

            <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'var(--accent-crimson)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: '600' }}>
              <LogOut size={16} />
              LOGOUT
            </button>
          </div>
        )}
      </header>

      <main>
        {view === 'auth' && <Auth onLogin={handleLogin} />}
        
        {view === 'dashboard' && (
          <Dashboard 
            onNew={() => setView('intake')} 
            onViewReport={handleViewHistoricalReport} 
          />
        )}
        
        {view === 'intake' && (
          <IntakeForm 
            onSubmit={handleStartRun} 
            runError={runError} 
          />
        )}
        
        {view === 'pipeline' && (
          <Pipeline 
            jobId={currentJobId} 
            onComplete={handleJobComplete}
            onFail={(job) => {
              setRunError(job.error || 'Pipeline execution failed.');
              setView('report');
            }}
          />
        )}
        
        {view === 'report' && (
          <Report 
            subject={currentSubject} 
            report={currentReport}
            runError={runError}
          />
        )}
      </main>

      <footer style={{ marginTop: '80px', paddingTop: '32px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
        <p>&copy; {new Date().getFullYear()} Inkognito Matrimonial Verification Pipelines. All rights reserved.</p>
        <p style={{ marginTop: '8px', opacity: 0.6 }}>Strictly for personal pre-matrimonial due diligence. Statutory retrieval from public records only.</p>
      </footer>
    </div>
  );
}

export default App;
