const { useState, useEffect } = React;

console.log("🕯️ Inkognito Frontend Initializing...");

// --- API Service ---
const API_URL = '/api';
const getAuthHeaders = () => {
    const token = localStorage.getItem('inkognito_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};
const handleRes = async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
};
const api = {
    login: (u, p) => fetch(`${API_URL}/login`, { method: 'POST', body: JSON.stringify({username:u, password:p}) }).then(handleRes),
    reg: (u, p) => fetch(`${API_URL}/register`, { method: 'POST', body: JSON.stringify({username:u, password:p}) }).then(handleRes),
    user: () => fetch(`${API_URL}/user`, { headers: getAuthHeaders() }).then(handleRes),
    reports: () => fetch(`${API_URL}/reports`, { headers: getAuthHeaders() }).then(handleRes),
    status: (id) => fetch(`${API_URL}/jobs/${id}`, { headers: getAuthHeaders() }).then(handleRes),
    run: (p) => fetch(`${API_URL}/run`, { method: 'POST', headers: {...getAuthHeaders(), 'Content-Type': 'application/json'}, body: JSON.stringify(p) }).then(handleRes)
};

// --- Components ---

function Icon({ name, size = 18, color = "currentColor", className = "" }) {
    useEffect(() => {
        try { if (window.lucide) window.lucide.createIcons(); } catch(e) {}
    }, [name]);
    return <i data-lucide={name} className={className} style={{ width: size, height: size, color: color, display: 'inline-block' }}></i>;
}

function Auth({ onLogin }) {
    const [isLogin, setIsLogin] = useState(true);
    const [u, setU] = useState('');
    const [p, setP] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const submit = async (e) => {
        e.preventDefault(); setLoading(true); setError('');
        try {
            if (isLogin) {
                const res = await api.login(u, p);
                localStorage.setItem('inkognito_token', res.token);
                const user = await api.user();
                onLogin(user);
            } else { await api.reg(u, p); setIsLogin(true); alert('Registered!'); }
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    return (
        <div className="fade-in" style={{ display:'flex', justifyContent:'center', minHeight:'60vh', alignItems:'center' }}>
            <div className="panel" style={{ width: '100%', maxWidth: '400px' }}>
                <div style={{ textAlign:'center', marginBottom:'32px' }}>
                    <Icon name="shield-check" size={48} color="var(--accent-gold)" />
                    <h2 className="serif-heading" style={{ fontSize:'2rem', marginTop:'16px' }}>{isLogin ? 'Authentication' : 'Registration'}</h2>
                </div>
                {error && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px', textAlign:'center' }}>{error}</div>}
                <form onSubmit={submit}>
                    <div style={{ marginBottom:'16px' }}>
                        <label className="input-label">Username</label>
                        <input type="text" value={u} onChange={e => setU(e.target.value)} required />
                    </div>
                    <div style={{ marginBottom:'24px' }}>
                        <label className="input-label">Password</label>
                        <input type="password" value={p} onChange={e => setP(e.target.value)} required />
                    </div>
                    <button className="btn btn-primary" style={{ width:'100%' }} disabled={loading}>
                        {loading ? <Icon name="loader-2" className="spin" /> : (isLogin ? 'LOG IN' : 'SIGN UP')}
                    </button>
                </form>
                <div style={{ textAlign:'center', marginTop:'24px' }}>
                    <button onClick={() => setIsLogin(!isLogin)} style={{ background:'none', border:'none', color:'var(--accent-gold)', cursor:'pointer' }}>
                        {isLogin ? "Create an account" : "Back to login"}
                    </button>
                </div>
            </div>
        </div>
    );
}

function Dashboard({ onNew, onViewReport }) {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.reports().then(setReports).finally(() => setLoading(false));
    }, []);

    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'40px' }}>
                <h2 className="serif-heading" style={{ fontSize:'2rem' }}>Archived Verifications</h2>
                <button className="btn btn-primary" onClick={onNew}><Icon name="plus" /> New Verification</button>
            </div>
            {loading ? <div style={{ textAlign:'center', padding:'60px' }}><Icon name="loader-2" className="spin" size={32} /></div> :
            (!reports || reports.length === 0) ? <div className="panel" style={{ textAlign:'center' }}>No historical data found.</div> :
            <div style={{ display:'grid', gap:'12px' }}>
                {reports.map(r => (
                    <div key={r.report_id} className="panel" onClick={() => onViewReport(r)} style={{ cursor:'pointer', display:'flex', justifyContent:'space-between', padding:'16px 24px' }}>
                        <div style={{ display:'flex', gap:'16px', alignItems:'center' }}>
                            <Icon name="user" color="var(--accent-gold)" />
                            <div>
                                <div style={{ fontWeight:600 }}>{r.subject_name}</div>
                                <div style={{ fontSize:'0.75rem', color:'var(--text-muted)' }}>{new Date(r.generated_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                        <Icon name="chevron-right" color="var(--text-muted)" />
                    </div>
                ))}
            </div>}
        </div>
    );
}

function IntakeForm({ onSubmit, err, onBack }) {
    const [f, setF] = useState({ name:'', phone:'', city:'', employer:'', business:'', socialUrls:'' });
    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'32px' }}>
                <h2 className="serif-heading" style={{ fontSize:'2rem' }}>Subject Intake</h2>
                <button className="btn btn-outline" onClick={onBack}>Cancel</button>
            </div>
            <form onSubmit={e => { e.preventDefault(); onSubmit(f); }}>
                <div className="panel" style={{ display:'grid', gap:'20px', marginBottom:'24px' }}>
                    <div className="input-group"><label className="input-label">Full Name *</label><input value={f.name} onChange={e => setF({...f, name:e.target.value})} required /></div>
                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px' }}>
                        <div className="input-group"><label className="input-label">Mobile *</label><input value={f.phone} onChange={e => setF({...f, phone:e.target.value})} required /></div>
                        <div className="input-group"><label className="input-label">City *</label><input value={f.city} onChange={e => setF({...f, city:e.target.value})} required /></div>
                    </div>
                </div>
                {err && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px' }}>{err}</div>}
                <button className="btn btn-primary" style={{ width:'100%', padding:'16px' }}>Start Verification</button>
            </form>
        </div>
    );
}

function Pipeline({ jobId, onComplete, onFail }) {
    const [job, setJob] = useState(null);
    useEffect(() => {
        const poll = () => api.status(jobId).then(d => {
            setJob(d);
            if (d.status === 'completed') onComplete(d);
            else if (d.status === 'failed') onFail(d);
        });
        poll(); const i = setInterval(poll, 2000); return () => clearInterval(i);
    }, [jobId]);
    if (!job) return <div style={{ textAlign:'center', padding:'60px' }}><Icon name="loader-2" className="spin" size={32} /></div>;
    return (
        <div className="fade-in">
            <h2 className="serif-heading" style={{ textAlign:'center', marginBottom:'40px' }}>Pipeline Running</h2>
            <div style={{ display:'grid', gap:'10px', maxWidth:'500px', margin:'0 auto' }}>
                {job.modules.map(m => (
                    <div key={m.name} className="panel" style={{ padding:'12px 24px', display:'flex', justifyContent:'space-between' }}>
                        <span>{m.name}</span>
                        <span style={{ fontSize:'0.8rem', color:'var(--accent-gold)' }}>{m.status.toUpperCase()}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function Report({ report, onClose }) {
    if (!report) return null;
    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'32px' }}>
                <h1 className="serif-heading" style={{ fontSize:'2.5rem' }}>{report.subject_name}</h1>
                <button className="btn btn-outline" onClick={onClose}>Close Report</button>
            </div>
            {Object.entries(report.modules_run || {}).map(([n, m]) => m.ran && (
                <div key={n} className="panel" style={{ marginBottom:'20px' }}>
                    <h4>{n}</h4>
                    {m.findings && m.findings.length > 0 ? m.findings.map((f, i) => (
                        <div key={i} style={{ marginTop:'12px', padding:'12px', background:'var(--bg-input)', borderRadius:'8px' }}>
                            <div style={{ fontWeight:600 }}>{f.title}</div>
                            <div style={{ fontSize:'0.9rem', color:'var(--text-muted)' }}>{f.detail}</div>
                        </div>
                    )) : <p style={{ marginTop:'12px', fontSize:'0.9rem', color:'var(--text-muted)' }}>No findings recorded.</p>}
                </div>
            ))}
        </div>
    );
}

// --- App Root ---

function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('loading');
    const [jobId, setJobId] = useState(null);
    const [rep, setRep] = useState(null);
    const [err, setErr] = useState('');

    useEffect(() => {
        const token = localStorage.getItem('inkognito_token');
        if (token) {
            api.user().then(u => { setUser(u); setView('dashboard'); }).catch(() => { localStorage.removeItem('inkognito_token'); setView('auth'); });
        } else { setView('auth'); }
    }, []);

    if (view === 'loading') return <div className="app-container" style={{ textAlign:'center', padding:'100px' }}><Icon name="loader-2" className="spin" size={48} /></div>;

    return (
        <div className="app-container">
            <header style={{ marginBottom:'60px', borderBottom:'1px solid var(--border-subtle)', paddingBottom:'32px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                    <div onClick={() => setView('dashboard')} style={{ cursor:'pointer' }}>
                        <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                            <Icon name="shield-check" color="var(--accent-gold)" size={24} />
                            <h1 className="serif-heading" style={{ fontSize: '1.8rem', color: 'var(--accent-gold)', letterSpacing:'0.05em' }}>INKOGNITO</h1>
                        </div>
                        <p style={{ fontSize: '0.7rem', color: 'var(--accent-gold)', marginTop: '4px', letterSpacing:'0.1em', fontWeight:600 }}>PUBLIC RECORDS DATA AGGREGATION SERVICE</p>
                    </div>
                    {user && (
                        <div style={{ display:'flex', alignItems:'center', gap:'20px' }}>
                            <div style={{ display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem' }}>
                                <Icon name="user" size={14} color="var(--text-muted)" />
                                <span style={{ color:'var(--text-muted)', textTransform:'uppercase' }}>LOGGED IN AS</span>
                                <span style={{ fontWeight:700 }}>{user.username}</span>
                            </div>
                            <button className="btn btn-outline" style={{ padding:'6px 16px', fontSize:'0.75rem' }} onClick={() => { localStorage.removeItem('inkognito_token'); setUser(null); setView('auth'); }}>LOGOUT</button>
                        </div>
                    )}
                </div>
            </header>

            <main>
                {view === 'auth' && <Auth onLogin={u => { setUser(u); setView('dashboard'); }} />}
                {view === 'dashboard' && <Dashboard onNew={() => { console.log("Navigating to Intake..."); setView('intake'); }} onViewReport={r => {
                    api.status(`report-${r.report_id}`).then(d => { setRep(d.report); setView('report'); });
                }} />}
                {view === 'intake' && <IntakeForm err={err} onBack={() => setView('dashboard')} onSubmit={f => {
                    setErr('');
                    api.run(f).then(d => { setJobId(d.job_id); setView('pipeline'); }).catch(e => setErr(e.message));
                }} />}
                {view === 'pipeline' && <Pipeline jobId={jobId} onComplete={d => { setRep(d.report); setView('report'); }} onFail={d => setErr(d.error)} />}
                {view === 'report' && <Report report={rep} onClose={() => setView('dashboard')} />}
            </main>
        </div>
    );
}

// Start App
const rootElement = document.getElementById('root');
if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    root.render(<App />);
}
