console.log("🚀 Inkognito Booting...");

window.onerror = function(msg, url, lineNo, columnNo, error) {
    alert("❌ RUNTIME ERROR: " + msg + "\nAt: " + lineNo + ":" + columnNo);
    return false;
};
window.onunhandledrejection = function(event) {
    alert("❌ PROMISE ERROR: " + event.reason);
};

// --- API ---
const API_URL = '/api';
const getAuthHeaders = () => ({ 'Authorization': `Bearer ${localStorage.getItem('inkognito_token') || ''}` });
const handleResponse = async (r) => {
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || 'Network Error');
    return d;
};
const api = {
    login: (u, p) => fetch(`${API_URL}/login`, { method:'POST', body:JSON.stringify({username:u, password:p}) }).then(handleResponse),
    reg: (u, p) => fetch(`${API_URL}/register`, { method:'POST', body:JSON.stringify({username:u, password:p}) }).then(handleResponse),
    reports: () => fetch(`${API_URL}/reports`, { headers:getAuthHeaders() }).then(handleResponse),
    user: () => fetch(`${API_URL}/user`, { headers:getAuthHeaders() }).then(handleResponse),
    status: (id) => fetch(`${API_URL}/jobs/${id}`, { headers:getAuthHeaders() }).then(handleResponse),
    run: (p) => fetch(`${API_URL}/run`, { method:'POST', headers:{...getAuthHeaders(), 'Content-Type':'application/json'}, body:JSON.stringify(p) }).then(handleResponse)
};

// --- Components ---

function Icon({ name, size = 18, color = "currentColor", className = "" }) {
    React.useEffect(() => {
        try { if (window.lucide) window.lucide.createIcons(); } catch(e) { console.error("Lucide Error", e); }
    }, [name]);
    return <i data-lucide={name} className={className} style={{ width: size, height: size, color: color, display: 'inline-block' }}></i>;
}

function Auth({ onLogin }) {
    const [u, setU] = React.useState('');
    const [p, setP] = React.useState('');
    const [err, setErr] = React.useState('');
    const [submitting, setSubmitting] = React.useState(false);

    const onSubmit = (e) => {
        e.preventDefault(); setSubmitting(true); setErr('');
        api.login(u, p).then(d => {
            localStorage.setItem('inkognito_token', d.token);
            api.user().then(onLogin);
        }).catch(e => setErr(e.message)).finally(() => setSubmitting(false));
    };

    return (
        <div style={{ display:'flex', justifyContent:'center', paddingTop:'100px' }}>
            <div className="panel" style={{ width:'100%', maxWidth:'400px' }}>
                <div style={{ textAlign:'center', marginBottom:'32px' }}>
                    <Icon name="shield-check" size={48} color="var(--accent-gold)" />
                    <h2 className="serif-heading" style={{ marginTop:'16px' }}>SECURE ACCESS</h2>
                </div>
                {err && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px', textAlign:'center', fontSize:'0.9rem' }}>{err}</div>}
                <form onSubmit={onSubmit}>
                    <div style={{ marginBottom:'16px' }}>
                        <label className="input-label">Username</label>
                        <input value={u} onChange={e => setU(e.target.value)} required />
                    </div>
                    <div style={{ marginBottom:'24px' }}>
                        <label className="input-label">Password</label>
                        <input type="password" value={p} onChange={e => setP(e.target.value)} required />
                    </div>
                    <button className="btn btn-primary" style={{ width:'100%' }} disabled={submitting}>
                        {submitting ? <Icon name="loader-2" className="spin" /> : 'INITIALIZE SESSION'}
                    </button>
                </form>
            </div>
        </div>
    );
}

function Dashboard({ onNew, onViewReport }) {
    const [reports, setReports] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        api.reports().then(setReports).finally(() => setLoading(false));
    }, []);

    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'40px' }}>
                <h2 className="serif-heading" style={{ fontSize:'2.2rem' }}>Archival Hub</h2>
                <button className="btn btn-primary" onClick={onNew}><Icon name="plus" /> New Verification</button>
            </div>
            {loading ? <div style={{ textAlign:'center', padding:'60px' }}><Icon name="loader-2" className="spin" size={32} /></div> :
            (!reports || !Array.isArray(reports) || reports.length === 0) ? <div className="panel" style={{ textAlign:'center' }}>No historical records found.</div> :
            <div style={{ display:'grid', gap:'12px' }}>
                {reports.map(r => (
                    <div key={r.report_id} className="panel" onClick={() => onViewReport(r)} style={{ cursor:'pointer', display:'flex', justifyContent:'space-between', padding:'16px 24px' }}>
                        <div style={{ display:'flex', gap:'16px', alignItems:'center' }}>
                            <Icon name="user" color="var(--accent-gold)" />
                            <div>
                                <div style={{ fontWeight:600 }}>{r.subject_name}</div>
                                <div style={{ fontSize:'0.75rem', color:'var(--text-muted)' }}>{r.generated_at}</div>
                            </div>
                        </div>
                        <Icon name="arrow-right" color="var(--text-muted)" />
                    </div>
                ))}
            </div>}
        </div>
    );
}

function Intake({ onSubmit, onBack, error }) {
    console.log("Rendering Intake Form...");
    const [f, setF] = React.useState({ name:'', phone:'', city:'' });
    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'40px' }}>
                <h2 className="serif-heading" style={{ fontSize:'2.2rem' }}>Subject Intake</h2>
                <button className="btn btn-outline" onClick={onBack}>Cancel</button>
            </div>
            <div className="panel">
                <form onSubmit={e => { e.preventDefault(); onSubmit(f); }}>
                    <div style={{ display:'grid', gap:'24px' }}>
                        <div><label className="input-label">Identified Full Name *</label><input value={f.name} onChange={e => setF({...f, name:e.target.value})} required /></div>
                        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px' }}>
                            <div><label className="input-label">Mobile Number *</label><input value={f.phone} onChange={e => setF({...f, phone:e.target.value})} required /></div>
                            <div><label className="input-label">Target City *</label><input value={f.city} onChange={e => setF({...f, city:e.target.value})} required /></div>
                        </div>
                        {error && <div style={{ color:'var(--accent-crimson)', fontSize:'0.9rem' }}>{error}</div>}
                        <button className="btn btn-primary" style={{ padding:'16px', width:'100%' }}>Initiate Pipeline</button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// --- App ---

function App() {
    console.log("App Rendering...");
    const [user, setUser] = React.useState(null);
    const [view, setView] = React.useState('loading'); // loading, auth, dashboard, intake, pipeline, report
    const [jobId, setJobId] = React.useState('');
    const [report, setReport] = React.useState(null);
    const [err, setErr] = React.useState('');

    React.useEffect(() => {
        const token = localStorage.getItem('inkognito_token');
        if (token) api.user().then(u => { setUser(u); setView('dashboard'); }).catch(() => { localStorage.removeItem('inkognito_token'); setView('auth'); });
        else setView('auth');
    }, []);

    const logout = () => { localStorage.removeItem('inkognito_token'); setUser(null); setView('auth'); };

    if (view === 'loading') return <div style={{ padding:'100px', textAlign:'center', color:'var(--accent-gold)' }}><Icon name="loader-2" className="spin" size={48} /></div>;

    return (
        <div className="app-container">
            <header style={{ marginBottom:'60px', borderBottom:'1px solid var(--border-subtle)', paddingBottom:'24px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                    <div onClick={() => user && setView('dashboard')} style={{ cursor:'pointer' }}>
                        <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                            <Icon name="shield-check" color="var(--accent-gold)" size={24} />
                            <h1 className="serif-heading" style={{ fontSize:'1.8rem', color:'var(--accent-gold)', letterSpacing:'0.05em' }}>INKOGNITO</h1>
                        </div>
                        <p style={{ fontSize:'0.65rem', color:'var(--accent-gold)', fontWeight:600, marginTop:'4px', letterSpacing:'0.15em' }}>PUBLIC RECORDS DATA AGGREGATION SERVICE</p>
                    </div>
                    {user && (
                        <div style={{ display:'flex', alignItems:'center', gap:'20px' }}>
                            <div style={{ display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem', opacity:0.8 }}>
                                <Icon name="user" size={14} />
                                <span>LOGGED IN AS</span>
                                <span style={{ fontWeight:700 }}>{user.username}</span>
                            </div>
                            <button className="btn btn-outline" style={{ padding:'6px 16px', fontSize:'0.75rem' }} onClick={logout}>LOGOUT</button>
                        </div>
                    )}
                </div>
            </header>

            <main>
                {view === 'auth' && <Auth onLogin={u => { setUser(u); setView('dashboard'); }} />}
                {view === 'dashboard' && <Dashboard 
                    onNew={() => { console.log("Button Clicked: New Verification"); setView('intake'); }} 
                    onViewReport={r => api.status(`report-${r.report_id}`).then(d => { setReport(d.report); setView('report'); })} 
                />}
                {view === 'intake' && <Intake error={err} onBack={() => setView('dashboard')} onSubmit={f => {
                    setErr('');
                    api.run(f).then(d => { setJobId(d.job_id); setView('pipeline'); }).catch(e => setErr(e.message));
                }} />}
                
                {view === 'pipeline' && (
                    <div style={{ textAlign:'center', padding:'60px' }}>
                        <Icon name="loader-2" className="spin" size={48} color="var(--accent-gold)" />
                        <h2 className="serif-heading" style={{ marginTop:'24px' }}>SEARCHING RECORDS...</h2>
                        <div style={{ fontSize:'0.8rem', opacity:0.5, marginTop:'10px' }}>JOB ID: {jobId}</div>
                    </div>
                )}

                {view === 'report' && (
                    <div className="fade-in">
                        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'32px', alignItems:'center' }}>
                            <h1 className="serif-heading" style={{ fontSize:'2.4rem' }}>{report?.subject_name}</h1>
                            <button className="btn btn-outline" onClick={() => setView('dashboard')}>Close Report</button>
                        </div>
                        {report?.modules_run && Object.entries(report.modules_run).map(([n, m]) => m.ran && (
                            <div key={n} className="panel" style={{ marginBottom:'20px' }}>
                                <h4 style={{ textTransform:'uppercase', letterSpacing:'0.1em', fontSize:'0.9rem', color:'var(--accent-gold)', marginBottom:'12px' }}>{n}</h4>
                                {m.findings?.length > 0 ? m.findings.map((f, i) => (
                                    <div key={i} style={{ padding:'16px', background:'var(--bg-input)', borderRadius:'8px', marginTop:'12px' }}>
                                        <div style={{ fontWeight:600 }}>{f.title}</div>
                                        <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)', marginTop:'4px' }}>{f.detail}</div>
                                    </div>
                                )) : <div style={{ fontSize:'0.85rem', color:'var(--text-muted)' }}>No adverse findings.</div>}
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

// Start
const r = ReactDOM.createRoot(document.getElementById('root'));
r.render(<App />);
