const { useState, useEffect } = React;

// --- API Service ---
const API_URL = '/api';
const getAuthHeaders = () => {
    const token = localStorage.getItem('inkognito_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};
const handleResponse = async (res) => {
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Network error' }));
        throw new Error(err.error || 'Something went wrong');
    }
    return res.json();
};
const api = {
    login: (u, p) => fetch(`${API_URL}/login`, { method: 'POST', body: JSON.stringify({username:u, password:p}) }).then(handleResponse),
    register: (u, p) => fetch(`${API_URL}/register`, { method: 'POST', body: JSON.stringify({username:u, password:p}) }).then(handleResponse),
    user: () => fetch(`${API_URL}/user`, { headers: getAuthHeaders() }).then(handleResponse),
    reports: () => fetch(`${API_URL}/reports`, { headers: getAuthHeaders() }).then(handleResponse),
    status: (id) => fetch(`${API_URL}/jobs/${id}`, { headers: getAuthHeaders() }).then(handleResponse),
    run: (p) => fetch(`${API_URL}/run`, { method: 'POST', headers: {...getAuthHeaders(), 'Content-Type': 'application/json'}, body: JSON.stringify(p) }).then(handleResponse)
};

// --- Components ---

function Icon({ name, size = 20, color = "currentColor", className = "" }) {
    useEffect(() => {
        if (window.lucide) window.lucide.createIcons();
    }, [name]);
    return <i data-lucide={name} style={{ width: size, height: size, color: color }} className={className}></i>;
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
                const userData = await api.user();
                onLogin(res.token, userData);
            } else {
                await api.register(u, p); setIsLogin(true); alert('Registered!');
            }
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    return (
        <div className="fade-in" style={{ display:'flex', justifyContent:'center', minHeight:'70vh', alignItems:'center' }}>
            <div className="panel" style={{ width: '100%', maxWidth: '400px' }}>
                <div style={{ textAlign:'center', marginBottom:'32px' }}>
                    <div style={{ background:'var(--accent-gold-soft)', padding:'12px', borderRadius:'12px', display:'inline-flex', marginBottom:'16px' }}>
                        <Icon name="shield-check" size={32} color="var(--accent-gold)" />
                    </div>
                    <h2 className="serif-heading" style={{ fontSize:'1.8rem' }}>{isLogin ? 'Welcome Back' : 'Join Inkognito'}</h2>
                </div>
                {error && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px', textAlign:'center' }}>{error}</div>}
                <form onSubmit={submit}>
                    <div className="input-group" style={{ marginBottom:'20px' }}>
                        <label className="input-label">Username</label>
                        <input type="text" value={u} onChange={e => setU(e.target.value)} required />
                    </div>
                    <div className="input-group" style={{ marginBottom:'24px' }}>
                        <label className="input-label">Password</label>
                        <input type="password" value={p} onChange={e => setP(e.target.value)} required />
                    </div>
                    <button className="btn btn-primary" style={{ width:'100%' }} disabled={loading}>
                        {loading ? <Icon name="loader-2" className="spin" /> : (isLogin ? 'Login' : 'Register')}
                    </button>
                </form>
                <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.9rem' }}>
                    <button onClick={() => setIsLogin(!isLogin)} style={{ background:'none', border:'none', color:'var(--accent-gold)', cursor:'pointer' }}>
                        {isLogin ? "Create account" : "Login instead"}
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
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'40px', borderBottom:'1px solid var(--border-subtle)', paddingBottom:'24px' }}>
                <div>
                    <h2 className="serif-heading" style={{ fontSize:'2.5rem' }}>Verification Hub</h2>
                </div>
                <button className="btn btn-primary" onClick={onNew}><Icon name="plus-circle" /> New Verification</button>
            </div>
            {loading ? <div style={{ textAlign:'center', padding:'100px' }}><Icon name="loader-2" className="spin" size={48} /></div> :
            reports.length === 0 ? <div className="panel" style={{ textAlign:'center' }}>No reports found. Start your first search.</div> :
            <div style={{ display:'grid', gap:'16px' }}>
                {reports.map(r => (
                    <div key={r.report_id} className="panel" onClick={() => onViewReport(r)} style={{ cursor:'pointer', display:'flex', justifyContent:'space-between' }}>
                        <div style={{ display:'flex', gap:'20px' }}>
                            <div style={{ background:'var(--accent-gold-soft)', padding:'12px', borderRadius:'10px' }}><Icon name="user" color="var(--accent-gold)" /></div>
                            <div>
                                <h4 style={{ fontSize:'1.2rem' }}>{r.subject_name}</h4>
                                <span style={{ color:'var(--text-muted)', fontSize:'0.8rem' }}>{new Date(r.generated_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                        <Icon name="chevron-right" color="var(--text-muted)" />
                    </div>
                ))}
            </div>}
        </div>
    );
}

function IntakeForm({ onSubmit, err }) {
    const [f, setF] = useState({ name:'', phone:'', city:'', employer:'', business:'', financeRole:false, socialUrls:'' });
    const sub = (e) => { e.preventDefault(); onSubmit(f); };
    return (
        <div className="fade-in">
            <h2 className="serif-heading" style={{ fontSize:'2rem', marginBottom:'32px' }}>Subject Identification</h2>
            <form onSubmit={sub}>
                <div className="panel" style={{ display:'grid', gap:'20px', marginBottom:'32px' }}>
                    <div className="input-group"><label className="input-label">Full Name *</label><input value={f.name} onChange={e => setF({...f, name:e.target.value})} required /></div>
                    <div className="input-group"><label className="input-label">Mobile Number *</label><input value={f.phone} onChange={e => setF({...f, phone:e.target.value})} required /></div>
                    <div className="input-group"><label className="input-label">Current City *</label><input value={f.city} onChange={e => setF({...f, city:e.target.value})} required /></div>
                </div>
                {err && <div style={{ color:'var(--accent-crimson)', marginBottom:'20px' }}>{err}</div>}
                <button className="btn btn-primary" style={{ width:'100%', padding:'16px' }}>Start Verification Pipeline</button>
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
        poll(); const intv = setInterval(poll, 2000); return () => clearInterval(intv);
    }, [jobId]);
    if (!job) return null;
    return (
        <div className="fade-in">
            <div style={{ textAlign:'center', marginBottom:'48px' }}>
                <Icon name="loader-2" className="spin" size={40} color="var(--accent-gold)" />
                <h2 className="serif-heading" style={{ fontSize:'2.2rem' }}>Pipeline Active</h2>
            </div>
            <div style={{ display:'grid', gap:'12px', maxWidth:'600px', margin:'0 auto' }}>
                {job.modules.map(m => (
                    <div key={m.name} className="panel" style={{ padding:'16px 24px', display:'flex', justifyContent:'space-between', borderColor: m.status === 'running' ? 'var(--accent-gold)' : 'var(--border-subtle)' }}>
                        <span>{m.name}</span>
                        <span style={{ fontSize:'0.8rem', color:'var(--text-muted)' }}>{m.status.toUpperCase()}</span>
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
            <div className="panel" style={{ borderLeft:'6px solid var(--accent-gold)', marginBottom:'32px', display:'flex', justifyContent:'space-between' }}>
                <div>
                    <h1 className="serif-heading" style={{ fontSize:'2.4rem' }}>{report.subject_name}</h1>
                    <p style={{ color:'var(--text-muted)' }}>REPORT ID: {report.report_id}</p>
                </div>
                <button className="btn btn-outline" onClick={onClose}>Back</button>
            </div>
            <div style={{ display: 'grid', gap: '24px' }}>
                {Object.entries(report.modules_run || {}).map(([name, m]) => m.ran && (
                    <div key={name} className="panel">
                        <h4>{name}</h4>
                        {m.findings?.length > 0 ? m.findings.map((f, i) => (
                            <div key={i} style={{ marginTop:'16px', padding:'12px', background:'var(--bg-input)', borderRadius:'8px' }}>
                                <h5>{f.title}</h5>
                                <p style={{ color:'var(--text-secondary)', fontSize:'0.9rem' }}>{f.detail}</p>
                            </div>
                        )) : <p style={{ color:'var(--text-muted)', marginTop:'12px' }}>No findings detected.</p>}
                    </div>
                ))}
            </div>
        </div>
    );
}

// --- Main App ---
function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('auth'); // auth, dashboard, intake, pipeline, report
    const [jobId, setJobId] = useState(null);
    const [rep, setRep] = useState(null);
    const [err, setErr] = useState('');

    useEffect(() => {
        const token = localStorage.getItem('inkognito_token');
        if (token) api.user().then(u => { setUser(u); setView('dashboard'); }).catch(() => localStorage.removeItem('inkognito_token'));
    }, []);

    if (!user && view === 'auth') return <div className="app-container"><Auth onLogin={(t, u) => { setUser(u); setView('dashboard'); }} /></div>;

    return (
        <div className="app-container">
            <header style={{ marginBottom:'48px', display:'flex', justifyContent:'space-between' }}>
                <h1 className="serif-heading" style={{ color:'var(--accent-gold)', cursor:'pointer' }} onClick={() => setView('dashboard')}>INKOGNITO</h1>
                {user && <button className="btn btn-outline" onClick={() => { localStorage.removeItem('inkognito_token'); setUser(null); setView('auth'); }}>Logout</button>}
            </header>
            {view === 'dashboard' && <Dashboard onNew={() => setView('intake')} onViewReport={(r) => { 
                api.status(`report-${r.report_id}`).then(d => { setRep(d.report); setView('report'); });
            }} />}
            {view === 'intake' && <IntakeForm err={err} onSubmit={f => api.run(f).then(d => { setJobId(d.job_id); setView('pipeline'); }).catch(e => setErr(e.message))} />}
            {view === 'pipeline' && <Pipeline jobId={jobId} onComplete={d => { setRep(d.report); setView('report'); }} onFail={d => setErr(d.error)} />}
            {view === 'report' && <Report report={rep} onClose={() => setView('dashboard')} />}
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
