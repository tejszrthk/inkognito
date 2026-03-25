const { useState, useEffect } = React;

// --- API Service ---
const API_URL = '/api';
const getAuthHeaders = () => {
    const token = localStorage.getItem('inkognito_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};
const handleRes = async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Network request failed');
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

// --- Icons ---
const Icon = ({ name, size = 18, color = "currentColor", className = "" }) => {
    useEffect(() => {
        try { if (window.lucide) window.lucide.createIcons(); } catch(e) {}
    }, [name]);
    return <i data-lucide={name} className={className} style={{ width: size, height: size, color: color, display: 'inline-block' }}></i>;
};

// --- Sub-Components ---

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
            } else {
                await api.reg(u, p); setIsLogin(true); alert('Registration successful. Please login.');
            }
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    return (
        <div className="fade-in" style={{ display:'flex', justifyContent:'center', minHeight:'60vh', alignItems:'center' }}>
            <div className="panel" style={{ width: '100%', maxWidth: '380px' }}>
                <div style={{ textAlign:'center', marginBottom:'32px' }}>
                    <Icon name="shield-check" size={40} color="var(--accent-gold)" />
                    <h2 className="serif-heading" style={{ fontSize:'1.8rem', marginTop:'16px' }}>{isLogin ? 'Private Access' : 'Create Credentials'}</h2>
                </div>
                {error && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px', textAlign:'center', fontSize:'0.9rem' }}>{error}</div>}
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
                        {loading ? <Icon name="loader-2" className="spin" /> : (isLogin ? 'Initialize Session' : 'Register')}
                    </button>
                </form>
                <div style={{ textAlign:'center', marginTop:'24px' }}>
                    <button onClick={() => setIsLogin(!isLogin)} style={{ background:'none', border:'none', color:'var(--accent-gold)', cursor:'pointer', fontSize:'0.9rem' }}>
                        {isLogin ? "Need an account? Register" : "Have an account? Login"}
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
        api.reports().then(setReports).catch(e => console.error(e)).finally(() => setLoading(false));
    }, []);

    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'40px' }}>
                <h2 className="serif-heading" style={{ fontSize:'2.2rem' }}>Archival Records</h2>
                <button className="btn btn-primary" onClick={onNew}><Icon name="plus" /> New Run</button>
            </div>
            {loading ? <div style={{ textAlign:'center', padding:'60px' }}><Icon name="loader-2" className="spin" size={32} /></div> :
            (!reports || reports.length === 0) ? <div className="panel" style={{ textAlign:'center', padding:'60px' }}>No verification history found.</div> :
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
                        <Icon name="arrow-right" color="var(--text-muted)" />
                    </div>
                ))}
            </div>}
        </div>
    );
}

function IntakeForm({ onSubmit, err, onBack }) {
    const [f, setF] = useState({ name:'', phone:'', city:'', employer:'', business:'', financeRole:false, socialUrls:'' });
    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'32px' }}>
                <h2 className="serif-heading" style={{ fontSize:'1.8rem' }}>Subject Intake</h2>
                <button className="btn btn-outline" onClick={onBack} style={{ padding:'8px 16px', fontSize:'0.8rem' }}>Cancel</button>
            </div>
            <form onSubmit={e => { e.preventDefault(); onSubmit(f); }}>
                <div className="panel" style={{ display:'grid', gap:'16px', marginBottom:'24px' }}>
                    <div><label className="input-label">Full Name *</label><input value={f.name} onChange={e => setF({...f, name:e.target.value})} required /></div>
                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'16px' }}>
                        <div><label className="input-label">Phone *</label><input type="tel" value={f.phone} onChange={e => setF({...f, phone:e.target.value})} required /></div>
                        <div><label className="input-label">City *</label><input value={f.city} onChange={e => setF({...f, city:e.target.value})} required /></div>
                    </div>
                    <div><label className="input-label">Social URLs (Optional)</label><input placeholder="LinkedIn / Instagram / Facebook" value={f.socialUrls} onChange={e => setF({...f, socialUrls:e.target.value})} /></div>
                </div>
                {err && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px', fontSize:'0.9rem' }}>{err}</div>}
                <button className="btn btn-primary" style={{ width:'100%', padding:'16px' }}>Activate Pipeline</button>
            </form>
        </div>
    );
}

function PipelineView({ jobId, onComplete, onFail }) {
    const [job, setJob] = useState(null);
    useEffect(() => {
        const poll = () => api.status(jobId).then(d => {
            setJob(d);
            if (d.status === 'completed') onComplete(d);
            else if (d.status === 'failed') onFail(d);
        }).catch(e => console.error(e));
        poll(); const intv = setInterval(poll, 2500); return () => clearInterval(intv);
    }, [jobId]);
    if (!job) return <div style={{ textAlign:'center', padding:'60px' }}><Icon name="loader-2" className="spin" size={32} /></div>;
    return (
        <div className="fade-in">
            <div style={{ textAlign:'center', marginBottom:'40px' }}>
                <Icon name="activity" className="spin" size={40} color="var(--accent-gold)" />
                <h2 className="serif-heading" style={{ fontSize:'2rem', marginTop:'16px' }}>Searching Statutory Records</h2>
                <div style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginTop:'8px' }}>Tracking Job: {jobId}</div>
            </div>
            <div style={{ display:'grid', gap:'10px', maxWidth:'500px', margin:'0 auto' }}>
                {job.modules.map(m => (
                    <div key={m.name} className="panel" style={{ padding:'12px 20px', display:'flex', justifyContent:'space-between', alignItems:'center', opacity: m.status === 'queued' ? 0.4 : 1 }}>
                        <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                            {m.status === 'running' ? <Icon name="loader-2" className="spin" size={16} /> : 
                             m.status === 'complete' ? <Icon name="check-circle" size={16} color="var(--accent-green)" /> :
                             <Icon name="circle" size={16} color="var(--text-muted)" />}
                            <span style={{ fontWeight:500 }}>{m.name}</span>
                        </div>
                        <span style={{ fontSize:'0.7rem' }}>{m.status.toUpperCase()}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ReportView({ report, onBack }) {
    if (!report) return null;
    return (
        <div className="fade-in">
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'32px' }}>
                <h1 className="serif-heading" style={{ fontSize:'2rem' }}>{report.subject_name}</h1>
                <button className="btn btn-outline" onClick={onBack}>Exit Report</button>
            </div>
            <div style={{ display:'grid', gap:'20px' }}>
                {report.modules_run && Object.entries(report.modules_run).map(([name, m]) => m.ran && (
                    <div key={name} className="panel">
                        <div style={{ display:'flex', justifyContent:'space-between', borderBottom:'1px solid var(--border-subtle)', paddingBottom:'12px', marginBottom:'16px' }}>
                            <h4 style={{ fontWeight:700 }}>{name}</h4>
                            <span style={{ fontSize:'0.8rem', color: m.success ? 'var(--accent-green)' : 'var(--accent-gold)' }}>
                                {m.success ? 'SECURE' : 'UNVERIFIED'}
                            </span>
                        </div>
                        {m.findings && m.findings.length > 0 ? m.findings.map((f, i) => (
                            <div key={i} style={{ padding:'12px', background:'var(--bg-input)', borderRadius:'8px', marginBottom:'12px' }}>
                                <div style={{ fontSize:'0.9rem', fontWeight:600 }}>{f.title}</div>
                                <div style={{ fontSize:'0.85rem', color:'var(--text-secondary)' }}>{f.detail}</div>
                            </div>
                        )) : <div style={{ fontSize:'0.85rem', color:'var(--text-muted)' }}>No adverse records found in this statutory database.</div>}
                    </div>
                ))}
            </div>
        </div>
    );
}

// --- App Root ---
function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('loading'); // loading, auth, dashboard, intake, pipeline, report
    const [jobId, setJobId] = useState(null);
    const [rep, setRep] = useState(null);
    const [err, setErr] = useState('');

    useEffect(() => {
        const token = localStorage.getItem('inkognito_token');
        if (token) {
            api.user()
                .then(u => { setUser(u); setView('dashboard'); })
                .catch(() => { localStorage.removeItem('inkognito_token'); setView('auth'); });
        } else {
            setView('auth');
        }
    }, []);

    const logout = () => { localStorage.removeItem('inkognito_token'); setUser(null); setView('auth'); };

    if (view === 'loading') return <div className="app-container" style={{ textAlign:'center', paddingTop:'100px' }}><Icon name="loader-2" className="spin" size={48} /></div>;
    if (view === 'auth') return <div className="app-container"><Auth onLogin={(u) => { setUser(u); setView('dashboard'); }} /></div>;

    return (
        <div className="app-container">
            <header style={{ marginBottom:'40px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <h1 className="serif-heading" style={{ color:'var(--accent-gold)', cursor:'pointer', fontSize:'1.5rem', letterSpacing:'0.1em' }} onClick={() => setView('dashboard')}>INKOGNITO</h1>
                <div style={{ display:'flex', gap:'20px', alignItems:'center' }}>
                    <span style={{ fontSize:'0.8rem', color:'var(--text-muted)' }}>{user?.username}</span>
                    <button className="btn btn-outline" onClick={logout} style={{ padding:'6px 12px', fontSize:'0.75rem' }}>Logout</button>
                </div>
            </header>
            
            <main>
                {view === 'dashboard' && <Dashboard onNew={() => setView('intake')} onViewReport={r => {
                    api.status(`report-${r.report_id}`).then(d => { setRep(d.report); setView('report'); });
                }} />}
                {view === 'intake' && <IntakeForm err={err} onBack={() => setView('dashboard')} onSubmit={f => {
                    setErr('');
                    api.run(f).then(d => { setJobId(d.job_id); setView('pipeline'); }).catch(e => setErr(e.message));
                }} />}
                {view === 'pipeline' && <PipelineView jobId={jobId} onComplete={d => { setRep(d.report); setView('report'); }} onFail={d => setErr(d.error)} />}
                {view === 'report' && <ReportView report={rep} onBack={() => setView('dashboard')} />}
            </main>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
