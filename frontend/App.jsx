const { useState, useEffect, useRef } = React;

const MODULE_CONFIG = [
  { id: 'ecourts', backendName: 'eCourts', name: 'eCourts District & High Court', defaultActive: true },
  { id: 'mca21', backendName: 'MCA21', name: 'MCA21 Directorships', defaultActive: false, trigger: 'business' },
  { id: 'gst', backendName: 'GST', name: 'GSTIN Registration', defaultActive: false, trigger: 'business' },
  { id: 'google', backendName: 'Google Search', name: 'Google Search Deep Dive', defaultActive: true },
  { id: 'property', backendName: 'Property Records', name: 'Property Registration Records', defaultActive: true },
  { id: 'social', backendName: 'Social Media', name: 'Social Media Footprint', defaultActive: true },
  { id: 'image', backendName: 'Reverse Image Search', name: 'Reverse Image & Face Search', defaultActive: true },
  { id: 'phone', backendName: 'Phone Intelligence', name: 'Phone Intelligence (Truecaller/UPI)', defaultActive: true },
  { id: 'matrimonial', backendName: 'Matrimonial Cross-check', name: 'Matrimonial Site Cross-check', defaultActive: true },
  { id: 'ncdrc', backendName: 'NCDRC', name: 'Consumer Court (NCDRC)', defaultActive: true },
  { id: 'nclt', backendName: 'NCLT', name: 'NCLT Tribunal Records', defaultActive: true },
  { id: 'sebi', backendName: 'SEBI', name: 'SEBI Enforcement Records', defaultActive: false, trigger: 'finance' },
  { id: 'epfo', backendName: 'EPFO', name: 'EPFO Employment History', defaultActive: false, trigger: 'employer' }
];

const MODULE_CONFIG_BY_ID = MODULE_CONFIG.reduce((acc, mod) => {
  acc[mod.id] = mod;
  return acc;
}, {});

const MODULE_ID_BY_BACKEND_NAME = MODULE_CONFIG.reduce((acc, mod) => {
  acc[mod.backendName] = mod.id;
  return acc;
}, {});

const API_BASE_STORAGE_KEY = 'inkognito_api_base';
const API_BASE_QUERY_PARAM = 'api_base';

function normalizeApiBaseUrl(rawUrl) {
  const value = String(rawUrl || '').trim();
  if (!value) return '';
  return value.replace(/\/+$/, '');
}

function readStoredApiBaseUrl() {
  try {
    return normalizeApiBaseUrl(window.localStorage.getItem(API_BASE_STORAGE_KEY));
  } catch (_err) {
    return '';
  }
}

function writeStoredApiBaseUrl(apiBase) {
  try {
    if (!apiBase) return;
    window.localStorage.setItem(API_BASE_STORAGE_KEY, apiBase);
  } catch (_err) {
    // localStorage may be unavailable in strict browser privacy modes.
  }
}

function resolveApiBaseUrl() {
  const fromQuery = normalizeApiBaseUrl(new URLSearchParams(window.location.search).get(API_BASE_QUERY_PARAM));
  if (fromQuery) {
    writeStoredApiBaseUrl(fromQuery);
    return fromQuery;
  }

  const fromWindowConfig = normalizeApiBaseUrl(window.INKOGNITO_API_BASE);
  if (fromWindowConfig) {
    writeStoredApiBaseUrl(fromWindowConfig);
    return fromWindowConfig;
  }

  const fromStorage = readStoredApiBaseUrl();
  if (fromStorage) {
    return fromStorage;
  }

  const localHosts = ['localhost', '127.0.0.1'];
  const isLocalHost = localHosts.includes(window.location.hostname);

  if (isLocalHost) {
    // If no explicit override, use the same host/port that served the page
    return '';
  }

  // For deployed frontend, default to same-origin /api unless explicitly overridden.
  return '';
}

const API_BASE_URL = resolveApiBaseUrl();

const AUTH_TOKEN_KEY = 'inkognito_auth_token';
const AUTH_USER_KEY = 'inkognito_auth_user';

function readStoredAuth() {
  try {
    const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
    const user = JSON.parse(window.localStorage.getItem(AUTH_USER_KEY) || 'null');
    return { token, user };
  } catch (_err) {
    return { token: null, user: null };
  }
}

function writeStoredAuth(token, user) {
  try {
    if (token) window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    else window.localStorage.removeItem(AUTH_TOKEN_KEY);
    
    if (user) window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    else window.localStorage.removeItem(AUTH_USER_KEY);
  } catch (_err) {}
}

function apiUrl(path) {
  if (!API_BASE_URL) return path;
  return `${API_BASE_URL}${path}`;
}

function getAuthHeaders(token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function summarizeNonJsonResponse(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return 'Empty response body';

  const lower = trimmed.toLowerCase();
  if (
    trimmed.startsWith('<!DOCTYPE') ||
    trimmed.startsWith('<html') ||
    lower.includes('<body') ||
    lower.includes('page could not') ||
    lower.startsWith('the page c')
  ) {
    return 'API endpoint returned HTML/text instead of JSON. Set window.INKOGNITO_API_BASE in deploy-config.js (for example, https://your-backend.example.com) or open with ?api_base=https://your-backend.example.com.';
  }

  return trimmed.length > 220 ? `${trimmed.slice(0, 220)}...` : trimmed;
}

async function parseApiResponse(response, actionLabel) {
  const raw = await response.text();
  let payload = null;

  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch (_err) {
      payload = null;
    }
  }

  if (!response.ok) {
    const message =
      (payload && (payload.error || payload.message)) ||
      summarizeNonJsonResponse(raw) ||
      `Request failed while trying to ${actionLabel}.`;
    throw new Error(message);
  }

  if (!payload || typeof payload !== 'object') {
    const details = summarizeNonJsonResponse(raw);
    throw new Error(`Unexpected non-JSON API response while trying to ${actionLabel}: ${details}`);
  }

  return payload;
}

const ICONS = {
  ShieldCheck: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>,
  AlertCircle: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>,
  CheckCircle: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  Clock: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  ChevronDown: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="6 9 12 15 18 9"/></svg>,
  ChevronUp: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="18 15 12 9 6 15"/></svg>,
  Search: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>,
  LogOut: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>,
  User: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
  FileText: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>,
  Download: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
};

function formatElapsed(secs) {
  const value = Number.isFinite(secs) ? Math.max(0, Math.floor(secs)) : 0;
  const minutes = Math.floor(value / 60).toString().padStart(2, '0');
  const seconds = (value % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

function normalizeJobModules(jobModules = []) {
  const byId = {};

  jobModules.forEach((mod) => {
    const fallbackId = MODULE_ID_BY_BACKEND_NAME[mod.name] || String(mod.name || '').toLowerCase().replace(/\s+/g, '-');
    const id = mod.id || fallbackId;
    const cfg = MODULE_CONFIG_BY_ID[id];

    byId[id] = {
      id,
      name: cfg ? cfg.name : (mod.name || id),
      backendName: cfg ? cfg.backendName : (mod.name || id),
      status: mod.status || 'queued',
      skipReason: mod.skipReason || '',
      error: mod.error || '',
      findingsCount: Number(mod.findingsCount || 0),
      durationSec: Number(mod.durationSec || 0),
      findings: Array.isArray(mod.findings) ? mod.findings : []
    };
  });

  return MODULE_CONFIG.map((cfg) => {
    if (byId[cfg.id]) return byId[cfg.id];
    return {
      id: cfg.id,
      name: cfg.name,
      backendName: cfg.backendName,
      status: 'queued',
      skipReason: '',
      error: '',
      findingsCount: 0,
      durationSec: 0,
      findings: []
    };
  });
}

function buildReportModules(report, snapshot) {
  if (report && report.modules_run) {
    return MODULE_CONFIG.map((cfg) => {
      const moduleReport = report.modules_run[cfg.backendName];
      if (!moduleReport) {
        return {
          id: cfg.id,
          name: cfg.name,
          status: 'skipped',
          statusText: 'No output',
          skipReason: '',
          error: '',
          findings: []
        };
      }

      const status = moduleReport.skipped
        ? 'skipped'
        : (moduleReport.success ? 'complete' : 'failed');

      let statusText = '';
      if (status === 'skipped') statusText = moduleReport.skip_reason || 'Skipped';
      else if (status === 'failed') statusText = moduleReport.error || 'Failed';
      else statusText = `${moduleReport.findings_count || 0} finding(s) in ${moduleReport.duration_sec || 0}s`;

      return {
        id: cfg.id,
        name: cfg.name,
        status,
        statusText,
        skipReason: moduleReport.skip_reason || '',
        error: moduleReport.error || '',
        findings: Array.isArray(moduleReport.findings) ? moduleReport.findings : []
      };
    });
  }

  const fallback = normalizeJobModules(snapshot && Array.isArray(snapshot.modules) ? snapshot.modules : []);
  return fallback.map((module) => {
    let statusText = 'Queued';
    if (module.status === 'running') statusText = 'Running';
    if (module.status === 'complete') statusText = `${module.findingsCount || 0} finding(s)`;
    if (module.status === 'failed') statusText = module.error || 'Failed';
    if (module.status === 'skipped') statusText = module.skipReason || 'Skipped';

    return {
      id: module.id,
      name: module.name,
      status: module.status,
      statusText,
      skipReason: module.skipReason,
      error: module.error,
      findings: []
    };
  });
}

function App() {
  const [auth, setAuth] = useState(() => readStoredAuth());
  const [view, setView] = useState(auth.token ? 'dashboard' : 'auth');
  const [form, setForm] = useState({
    name: '',
    phone: '',
    city: '',
    employer: '',
    business: '',
    financeRole: false,
    socialUrls: ''
  });

  const [runError, setRunError] = useState('');
  const [runJobId, setRunJobId] = useState('');
  const [jobSnapshot, setJobSnapshot] = useState(null);
  const [reportData, setReportData] = useState(null);

  useEffect(() => {
    writeStoredAuth(auth.token, auth.user);
  }, [auth]);

  const handleLogout = async () => {
    try {
      await fetch(apiUrl('/api/logout'), {
        method: 'POST',
        headers: getAuthHeaders(auth.token)
      });
    } catch (_err) {}
    setAuth({ token: null, user: null });
    setView('auth');
  };

  const activeModules = MODULE_CONFIG.map((mod) => {
    let active = mod.defaultActive;
    if (mod.trigger === 'business' && form.business.trim()) active = true;
    if (mod.trigger === 'employer' && form.employer.trim()) active = true;
    if (mod.trigger === 'finance' && form.financeRole) active = true;
    return { ...mod, active };
  });

  const handleRun = async (e) => {
    e.preventDefault();

    if (!form.name.trim() || !form.phone.trim() || !form.city.trim()) {
      alert('Name, Phone, and City are required.');
      return;
    }

    const payload = {
      name: form.name.trim(),
      phone: form.phone.trim(),
      city: form.city.trim(),
      employer: form.employer.trim(),
      business: form.business.trim(),
      financeRole: form.financeRole,
      socialUrls: form.socialUrls.trim()
    };

    setRunError('');
    setRunJobId('');
    setJobSnapshot(null);
    setReportData(null);

    try {
      const response = await fetch(apiUrl('/api/run'), {
        method: 'POST',
        headers: getAuthHeaders(auth.token),
        body: JSON.stringify(payload)
      });

      const data = await parseApiResponse(response, 'start verification run');

      setRunJobId(data.job_id || '');
      setJobSnapshot(data);
      setView('pipeline');
    } catch (err) {
      setRunError(err.message || 'Unable to start verification.');
      setView('input');
    }
  };

  const handleNewVerification = () => {
    setView('consent');
    setRunError('');
    setRunJobId('');
    setJobSnapshot(null);
    setReportData(null);
    setForm({
      name: '',
      phone: '',
      city: '',
      employer: '',
      business: '',
      financeRole: false,
      socialUrls: ''
    });
  };

  return (
    <div className="container">
      <header className="app-header">
        <div className="brand">
          <div className="brand-logo">
            <ICONS.ShieldCheck style={{ width: 28, height: 28, color: 'var(--accent-gold)' }} />
            INKOGNITO
          </div>
          <div className="brand-subtitle">Public Records Data Aggregation Service</div>
        </div>
        
        {auth.user && (
          <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div className="user-identity">
              <ICONS.User size={14} />
              <span>LOGGED IN AS <strong>{auth.user.username}</strong></span>
              <button className="btn-logout" onClick={handleLogout}>LOGOUT</button>
            </div>
            {(view === 'report' || view === 'input' || view === 'pipeline') && (
              <button className="btn-text" onClick={() => setView('dashboard')}>Dashboard</button>
            )}
            {view === 'report' && (
              <button className="btn-primary" onClick={handleNewVerification}>New Verification</button>
            )}
          </div>
        )}
      </header>

      {view === 'auth' && (
        <AuthView 
          onLogin={(token, user) => {
            setAuth({ token, user });
            setView('dashboard');
          }} 
        />
      )}

      {view === 'dashboard' && (
        <DashboardView 
          token={auth.token}
          onNew={() => setView('consent')}
          onViewReport={(report) => {
            setForm({
              name: report.subject_name || '',
              city: report.generated_at || '', // dummy for report view
              phone: '', employer: '', business: '', financeRole: false, socialUrls: ''
            });
            setReportData(null); // Fetch detail if needed, or just pass enough
            // For now, let's just trigger a pseudo-report view
            // In a real app we'd fetch the full JSON from report_path or another API
            // but the simplified backend only serves saved reports as files.
            // Let's assume the user can click and we fetch the detail.
            fetchReportDetail(report.report_id);
          }}
        />
      )}

      {view === 'input' && (
        <InputView
          form={form}
          setForm={setForm}
          activeModules={activeModules}
          handleRun={handleRun}
          runError={runError}
        />
      )}

      {view === 'pipeline' && (
        <PipelineView
          jobId={runJobId}
          initialModules={jobSnapshot && Array.isArray(jobSnapshot.modules) ? jobSnapshot.modules : []}
          onSnapshot={(snapshot) => setJobSnapshot(snapshot)}
          onComplete={(snapshot) => {
            setJobSnapshot(snapshot);
            setReportData(snapshot.report || null);
            setRunError('');
            setView('report');
          }}
          onFail={(snapshot) => {
            setJobSnapshot(snapshot);
            setReportData(snapshot.report || null);
            setRunError(snapshot.error || 'Run failed.');
            setView('report');
          }}
        />
      )}

      {view === 'report' && (
        <ReportView
          subject={form}
          snapshot={jobSnapshot}
          report={reportData}
          runError={runError}
        />
      )}
    </div>
  );

  async function fetchReportDetail(reportId) {
    try {
      // In this setup, we don't have a direct "get report by ID" API yet
      // but we can add a simple one or just simulate it.
      // Let's assume we want to show the report view.
      // We'll update the backend to support GET /api/reports/<id> if not already there
      // Wait, api_server.py doesn't have GET /api/reports/<id> yet.
      // I'll add it to the backend next.
      
      const response = await fetch(apiUrl(`/api/jobs/report-${reportId}`), {
        headers: getAuthHeaders(auth.token)
      });
      // This is a hack because JOBS are ephemeral. 
      // A better way is to serve the JSON files.
      // For now, I'll alert that it's coming soon if not found.
      if (response.ok) {
        const data = await response.json();
        setReportData(data.report);
        setJobSnapshot(data);
        setView('report');
      } else {
        alert("Report detail loading from disk not implemented in this demo backend. JOBS are in-memory only.");
      }
    } catch (err) {
      alert("Error loading report: " + err.message);
    }
  }
}

function ConsentView({ onAccept }) {
  const [checked, setChecked] = useState(false);
  const sections = [
    {
      title: 'Nature of Service',
      body: 'Inkognito is a Data Aggregation Platform. It aggregates publicly available statutory and government records (eCourts, MCA21, GST, EPFO, SEBI enforcement orders, property registries) to assist with personal pre-matrimonial due diligence. It is NOT a private detective agency or a licensed credit bureau.'
    },
    {
      title: 'As-Is Report',
      body: "Reports are automated snapshots of public records at the time of retrieval, provided 'as-is' without any warranty of accuracy or completeness. Government databases are subject to clerical errors and delays. A finding does not constitute a criminal conviction or a professional determination of guilt."
    },
    {
      title: 'Liability Cap',
      body: 'Our maximum liability for any claim is strictly capped to the fee you paid for this report. We are not liable for consequential damages, broken engagements, emotional distress, or reputational harm arising from any finding.'
    },
    {
      title: 'Restricted Use',
      body: 'This report is exclusively for your personal pre-matrimonial due diligence. Redistribution, publication, or commercial use is strictly prohibited. By accepting, you agree to indemnify Inkognito against any claim arising from misuse of the report.'
    },
    {
      title: 'Data Retention',
      body: 'Your billing and account data is retained for tax compliance. Report data is permanently deleted 30 days after delivery. You may request earlier deletion by contacting our grievance officer.'
    },
    {
      title: 'Your Consent Scope',
      body: 'By proceeding, you confirm that you are providing consent only for the processing of your own account and billing data. You are not providing consent on behalf of the subject of the report. The statutory records used (court records, company registries, property indices) are publicly mandated by law and do not require the subject\'s consent under Section 3(c)(ii) of the DPDP Act, 2023.'
    }
  ];

  return (
    <div className="form-container">
      <h2 className="serif-heading" style={{ fontSize: '2rem', marginBottom: '8px' }}>Terms of Service &amp; Consent</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Please read and accept the following before proceeding with a verification.</p>

      <div className="panel" style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {sections.map((section) => (
          <div key={section.title}>
            <div className="mono-data" style={{ color: 'var(--accent-gold)', marginBottom: '8px', fontSize: '0.7rem' }}>{section.title}</div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.65' }}>{section.body}</p>
          </div>
        ))}
      </div>

      <div className="panel">
        <label className="toggle-group" style={{ cursor: 'pointer', gap: '16px', alignItems: 'flex-start' }}>
          <input type="checkbox" style={{ display: 'none' }} checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          <div className="toggle-switch" style={{ flexShrink: 0, marginTop: '3px' }}></div>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-primary)', textTransform: 'none', lineHeight: '1.6' }}>
            I have read and understood the Terms of Service above. I confirm this report is for my personal pre-matrimonial due diligence only. I will not redistribute, publish, or misuse this report in any way.
          </span>
        </label>
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn-primary"
            disabled={!checked}
            style={{ opacity: checked ? 1 : 0.4, cursor: checked ? 'pointer' : 'not-allowed' }}
            onClick={onAccept}
          >
            Accept &amp; Continue
          </button>
        </div>
      </div>
    </div>
  );
}

function InputView({ form, setForm, activeModules, handleRun, runError }) {
  const apiEndpointLabel = API_BASE_URL || `${window.location.origin}/api`;

  return (
    <div className="form-container">
      <h2 className="serif-heading" style={{ fontSize: '2rem', marginBottom: '8px' }}>Subject Intake</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Enter known subject details. Live backend execution will run all selected modules.</p>
      <p className="mono-data" style={{ color: 'var(--text-secondary)', marginBottom: '18px' }}>API ENDPOINT: {apiEndpointLabel}</p>

      {runError && (
        <div className="panel" style={{ marginBottom: '18px', borderColor: 'rgba(200,42,42,0.45)' }}>
          <div className="mono-data" style={{ color: 'var(--accent-crimson)', marginBottom: '6px' }}>Run Error</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{runError}</p>
        </div>
      )}

      <div className="panel">
        <form onSubmit={handleRun} className="form-grid">
          <div className="form-group">
            <label>Full Legal Name</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g., Rohan Sharma" required />
          </div>
          <div className="form-group">
            <label>Primary Phone Number</label>
            <input type="text" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91 XXXXX XXXXX" required />
          </div>
          <div className="form-group full-width">
            <label>City &amp; State</label>
            <input type="text" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} placeholder="e.g., Mumbai, Maharashtra" required />
          </div>

          <div className="form-group">
            <label>Known Employer (Optional)</label>
            <input type="text" value={form.employer} onChange={(e) => setForm({ ...form, employer: e.target.value })} placeholder="If employed..." />
          </div>
          <div className="form-group">
            <label>Known Business/LLP (Optional)</label>
            <input type="text" value={form.business} onChange={(e) => setForm({ ...form, business: e.target.value })} placeholder="Company Name or DIN" />
          </div>

          <div className="form-group full-width">
            <label className="toggle-group" style={{ marginTop: '12px' }}>
              <input type="checkbox" style={{ display: 'none' }} checked={form.financeRole} onChange={(e) => setForm({ ...form, financeRole: e.target.checked })} />
              <div className="toggle-switch"></div>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-primary)', textTransform: 'none' }}>Subject handles financial operations or trading</span>
            </label>
          </div>

          <div className="form-group full-width" style={{ marginTop: '16px' }}>
            <label>Known Social Media / Public URLs (Comma separated)</label>
            <input type="text" value={form.socialUrls} onChange={(e) => setForm({ ...form, socialUrls: e.target.value })} placeholder="LinkedIn, Instagram, etc." />
          </div>

          <div className="form-group full-width" style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '24px' }}>
            <button type="submit" className="btn-primary">
              <ICONS.Search style={{ width: 18, height: 18 }} />
              Run Verification
            </button>
          </div>
        </form>
      </div>

      <div className="modules-preview">
        <div className="modules-preview-title">
          <ICONS.Clock style={{ width: 14, height: 14 }} />
          Estimated Pipeline Configuration ({activeModules.filter((m) => m.active).length} of {MODULE_CONFIG.length} modules active)
        </div>
        <div className="pill-list">
          {activeModules.map((mod) => (
            <div key={mod.id} className={`pill ${mod.active ? 'active' : ''}`}>
              {mod.name} {mod.active ? '' : '(Skipped)'}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PipelineView({ jobId, initialModules, onSnapshot, onComplete, onFail }) {
  const [modules, setModules] = useState(() => normalizeJobModules(initialModules));
  const [elapsed, setElapsed] = useState(0);
  const [currentModule, setCurrentModule] = useState('');
  const [pollError, setPollError] = useState('');
  const completionRef = useRef(false);

  useEffect(() => {
    setModules(normalizeJobModules(initialModules));
  }, [initialModules]);

  useEffect(() => {
    if (!jobId) return;
    completionRef.current = false;

    let disposed = false;

    const poll = async () => {
      try {
        const response = await fetch(apiUrl(`/api/jobs/${encodeURIComponent(jobId)}`), { cache: 'no-store' });
        const payload = await parseApiResponse(response, 'fetch run status');

        if (disposed) return;

        setElapsed(Math.floor(payload.elapsed_sec || 0));
        setCurrentModule(payload.current_module || '');
        setModules(normalizeJobModules(Array.isArray(payload.modules) ? payload.modules : []));
        setPollError('');

        if (typeof onSnapshot === 'function') onSnapshot(payload);

        if (!completionRef.current && payload.status === 'completed') {
          completionRef.current = true;
          onComplete(payload);
        }

        if (!completionRef.current && payload.status === 'failed') {
          completionRef.current = true;
          onFail(payload);
        }
      } catch (err) {
        if (disposed) return;
        setPollError(err.message || 'Polling error; retrying...');
      }
    };

    poll();
    const intervalId = setInterval(poll, 1500);

    return () => {
      disposed = true;
      clearInterval(intervalId);
    };
  }, [jobId, onSnapshot, onComplete, onFail]);

  const finished = modules.filter((m) => ['complete', 'failed', 'skipped'].includes(m.status)).length;
  const progressPct = modules.length > 0 ? (finished / modules.length) * 100 : 0;

  return (
    <div className="pipeline-container fade-in">
      <div className="tracker-header">
        <div>
          <h2 className="serif-heading" style={{ fontSize: '2rem', marginBottom: '8px' }}>Executing Verification</h2>
          <p className="mono-data" style={{ color: 'var(--accent-gold)' }}>Live Module Tracker /// Job {jobId || 'initialising'}</p>
          {currentModule && (
            <p className="mono-data" style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>CURRENT: {currentModule}</p>
          )}
          {pollError && (
            <p className="mono-data" style={{ color: 'var(--accent-crimson)', marginTop: '8px' }}>{pollError}</p>
          )}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="mono-data" style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>{formatElapsed(elapsed)}</div>
          <div className="mono-data" style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>ELAPSED</div>
        </div>
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={{ width: `${progressPct}%` }}></div>
      </div>

      <div className="module-grid">
        {modules.map((mod) => {
          let icon = <span style={{ width: 12, height: 12, borderRadius: 5, background: 'var(--text-secondary)' }} />;
          if (mod.status === 'running') icon = <div className="status-running" title="Running..." />;
          if (mod.status === 'complete') icon = <ICONS.CheckCircle size={16} />;
          if (mod.status === 'failed') icon = <ICONS.AlertCircle size={16} />;
          if (mod.status === 'skipped') icon = null;

          return (
            <div key={mod.id} className={`module-card ${mod.status}`} title={mod.skipReason || mod.error || ''}>
              <div className="module-info">
                <h4>{mod.name}</h4>
                <p>{mod.status === 'queued' ? 'QUEUED' : mod.status.toUpperCase()}</p>
              </div>
              <div className="status-icon">{icon}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReportView({ subject, snapshot, report, runError }) {
  const modules = buildReportModules(report, snapshot);

  const totalFindings = report ? Number(report.total_findings || 0) : 0;
  const highPriority = report ? Number(report.high_priority || 0) : 0;
  const mediumPriority = report ? Number(report.medium_priority || 0) : 0;
  const modulesExecuted = modules.filter((m) => m.status !== 'skipped').length;

  const reportRef = (report && report.report_id) || (snapshot && snapshot.report_id) || 'Pending';
  const generated = report && report.generated_at
    ? report.generated_at.replace('T', ' ').slice(0, 19) + ' UTC'
    : new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  const overallFlag = (report && report.overall_flag)
    || (snapshot && snapshot.status === 'failed' ? 'RUN FAILED' : 'PENDING RESULT');

  let badgeClass = 'clear';
  if ((snapshot && snapshot.status === 'failed') || highPriority > 0 || String(overallFlag).toUpperCase().includes('HIGH')) {
    badgeClass = 'high-risk';
  } else if (mediumPriority > 0 || String(overallFlag).toUpperCase().includes('MEDIUM')) {
    badgeClass = 'caution';
  }

  return (
    <div className="report-container fade-in">
      <div style={{
        background: 'rgba(212,175,55,0.07)',
        border: '1px solid rgba(212,175,55,0.3)',
        borderRadius: '4px',
        padding: '16px 20px',
        marginBottom: '28px',
        fontSize: '0.78rem',
        color: 'var(--text-secondary)',
        lineHeight: '1.6'
      }}>
        <span style={{ color: 'var(--accent-gold)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Legal Disclaimer  ·  Read Before Use</span>
        <p style={{ marginTop: '8px' }}>
          This report is an automated snapshot of publicly available statutory and government records retrieved at the timestamp above. It is provided strictly <strong style={{ color: 'var(--text-primary)' }}>&quot;as-is&quot;</strong> without any warranty of accuracy or completeness. It does not constitute a certified investigation, legal opinion, or professional due diligence advice. Government databases are subject to clerical errors and delays; verify adverse findings independently before taking action.
        </p>
      </div>

      {runError && (
        <div className="panel" style={{ marginBottom: '20px', borderColor: 'rgba(200,42,42,0.45)' }}>
          <div className="mono-data" style={{ color: 'var(--accent-crimson)', marginBottom: '6px' }}>Run Error</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{runError}</p>
        </div>
      )}

      <div className="report-header">
        <div className="report-title-group">
          <h1>{subject.name || 'Subject Unknown'}</h1>
          <div className="report-meta">
            <span className="mono-data">ID: {reportRef}</span>
            <span className="mono-data">GEN: {generated}</span>
            <span className="mono-data">LOC: {subject.city || 'Unverified'}</span>
            <button 
              className="btn-text" 
              onClick={() => window.print()} 
              style={{ padding: '0 8px', marginLeft: '8px', borderLeft: '1px solid var(--border-light)' }}
            >
              <ICONS.Download size={14} style={{ marginRight: '6px' }} />
              Download PDF
            </button>
          </div>
          {snapshot && snapshot.report_path && (
            <div className="mono-data" style={{ marginTop: '8px', color: 'var(--text-secondary)' }}>SAVED: {snapshot.report_path}</div>
          )}
        </div>
        <div className={`flag-badge ${badgeClass}`}>
          {badgeClass === 'clear' ? <ICONS.ShieldCheck size={18}/> : <ICONS.AlertCircle size={18}/>}
          {overallFlag}
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{totalFindings}</div>
          <div className="stat-label">Total Findings</div>
        </div>
        <div className="stat-card" style={highPriority > 0 ? { borderBottom: '3px solid var(--accent-crimson)' } : {}}>
          <div className="stat-value text-crimson">{highPriority}</div>
          <div className="stat-label">High Priority</div>
        </div>
        <div className="stat-card" style={mediumPriority > 0 ? { borderBottom: '3px solid var(--accent-amber)' } : {}}>
          <div className="stat-value text-amber">{mediumPriority}</div>
          <div className="stat-label">Medium Priority</div>
        </div>
        <div className="stat-card">
          <div className="stat-value text-gold">{modulesExecuted}</div>
          <div className="stat-label">Modules Executed</div>
        </div>
      </div>

      <div className="modules-accordion-container">
        <h3 className="serif-heading" style={{ fontSize: '1.5rem', marginBottom: '20px', borderBottom: '1px solid var(--border-light)', paddingBottom: '12px' }}>
          Detailed Findings — Public Statutory Records
        </h3>
        {modules.map((module) => (
          <AccordionItem key={module.id} module={module} />
        ))}
      </div>
    </div>
  );
}

function AccordionItem({ module }) {
  const [open, setOpen] = useState(false);
  const hasHigh = module.findings && module.findings.some((f) => String(f.priority || '').toUpperCase() === 'HIGH');

  let statusIcon = <ICONS.CheckCircle size={16} className="text-green" />;
  if (module.status === 'running' || module.status === 'queued') statusIcon = <div className="status-running" title="Running" />;
  if (module.status === 'skipped') statusIcon = <span style={{ color: 'var(--text-muted)' }}>-</span>;
  if (module.status === 'failed') statusIcon = <ICONS.AlertCircle size={16} className="text-crimson" />;
  if (module.status === 'complete' && hasHigh) statusIcon = <ICONS.AlertCircle size={16} className="text-crimson" />;

  return (
    <div className={`accordion-item ${hasHigh ? 'high-priority' : ''}`}>
      <button className="accordion-header" onClick={() => setOpen(!open)}>
        <div className="accordion-title-area">
          <div className="accordion-status">{statusIcon}</div>
          <div>
            <div className="accordion-title">{module.name}</div>
            <div className="accordion-subtitle">{module.statusText || module.status}</div>
          </div>
        </div>
        <div>
          {open ? <ICONS.ChevronUp size={20} className="text-muted"/> : <ICONS.ChevronDown size={20} className="text-muted"/>}
        </div>
      </button>

      {open && (
        <div className="accordion-content">
          {module.status === 'skipped' && <p>{module.skipReason || 'Module skipped.'}</p>}
          {module.status === 'failed' && <p style={{ color: 'var(--accent-crimson)' }}>{module.error || 'Module failed.'}</p>}
          {(module.status === 'running' || module.status === 'queued') && <p style={{ color: 'var(--text-muted)' }}>Awaiting module completion...</p>}
          {module.status === 'complete' && (!module.findings || module.findings.length === 0) && <p>No findings reported by this module.</p>}

          {module.findings && module.findings.map((finding, idx) => {
            const priority = String(finding.priority || '').toUpperCase();
            const iconClass = priority === 'HIGH' ? 'alert' : (priority === 'MEDIUM' ? 'warn' : 'info');
            return (
              <div key={idx} className="finding-row">
                <div className={`finding-icon ${iconClass}`}>
                  {(priority === 'LOW' || priority === 'NONE')
                    ? <ICONS.CheckCircle size={18}/>
                    : <ICONS.AlertCircle size={18}/>
                  }
                </div>
                <div className="finding-text">
                  <h5>
                    {finding.title || 'Finding'}
                    {priority === 'HIGH' && <span className="badge-red">CRITICAL</span>}
                  </h5>
                  <p>{finding.detail || ''}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AuthView({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const path = isLogin ? '/api/login' : '/api/register';
    try {
      const response = await fetch(apiUrl(path), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await parseApiResponse(response, isLogin ? 'log in' : 'register');

      if (isLogin) {
        onLogin(data.token, data.user);
      } else {
        alert('Registration successful! Please log in.');
        setIsLogin(true);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container fade-in">
      <div className="panel">
        <h2 className="serif-heading" style={{ textAlign: 'center', marginBottom: '24px' }}>
          {isLogin ? 'Login to Inkognito' : 'Create Account'}
        </h2>
        {error && (
          <div style={{ color: 'var(--accent-crimson)', fontSize: '0.85rem', marginBottom: '16px', textAlign: 'center' }}>
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              placeholder="Enter your username"
              required 
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder="••••••••"
              style={{ 
                background: 'var(--bg-deep)', 
                border: '1px solid var(--border-light)', 
                color: 'var(--text-primary)', 
                padding: '12px 16px',
                borderRadius: '2px'
              }}
              required 
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}>
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>
        <div className="auth-toggle">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? 'Register' : 'Login'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DashboardView({ token, onNew, onViewReport }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const response = await fetch(apiUrl('/api/reports'), {
          headers: getAuthHeaders(token)
        });
        const data = await parseApiResponse(response, 'fetch reports history');
        setReports(data || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, [token]);

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '32px' }}>
        <div>
          <h2 className="serif-heading" style={{ fontSize: '2.5rem' }}>Your Verifications</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Access all reports generated by your account.</p>
        </div>
        <button className="btn-primary" onClick={onNew}>
          <ICONS.Search size={18} />
          Run New Verification
        </button>
      </div>

      {loading ? (
        <div className="empty-state">Loading reports...</div>
      ) : error ? (
        <div className="panel" style={{ borderColor: 'var(--accent-crimson)' }}>
          <p style={{ color: 'var(--accent-crimson)' }}>Error: {error}</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="empty-state">
          <ICONS.FileText size={48} style={{ marginBottom: '16px', opacity: 0.2 }} />
          <p>No reports found. Start your first verification to see it here.</p>
        </div>
      ) : (
        <div className="reports-grid">
          {reports.map((report) => (
            <div key={report.report_id} className="report-item" onClick={() => onViewReport(report)}>
              <div className="report-item-info">
                <h4>{report.subject_name}</h4>
                <p>ID: {report.report_id}  ·  {new Date(report.generated_at).toLocaleString()}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="mono-data" style={{ color: 'var(--accent-gold)', fontSize: '0.7rem' }}>View Detail</span>
                <ICONS.ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const ICONS_EXT = {
  ChevronRight: (props) => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="9 18 15 12 9 6"/></svg>
};
// Merging extended icons
Object.assign(ICONS, ICONS_EXT);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
