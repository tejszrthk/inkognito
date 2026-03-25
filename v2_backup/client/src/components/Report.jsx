import React from 'react';
import { AlertTriangle, CheckCircle, Info, ChevronDown, Download, ExternalLink, Printer, ShieldAlert } from 'lucide-react';

export default function Report({ subject, snapshot, report, runError }) {
  if (runError) {
    return (
      <div className="panel" style={{ borderColor: 'var(--accent-crimson)', background: 'rgba(200, 42, 42, 0.05)' }}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <ShieldAlert size={64} color="var(--accent-crimson)" style={{ marginBottom: '24px' }} />
          <h2 className="serif-heading" style={{ color: 'var(--accent-crimson)', marginBottom: '12px' }}>Verification Disrupted</h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}> {runError} </p>
        </div>
      </div>
    );
  }

  const data = report || (snapshot && snapshot.report);
  if (!data) return null;

  const getFlagColor = (flag) => {
    if (flag.includes('HIGH')) return 'var(--accent-crimson)';
    if (flag.includes('MEDIUM')) return 'var(--accent-gold)';
    return 'var(--accent-green)';
  };

  return (
    <div className="fade-in">
      {/* Header & Status */}
      <div className="panel" style={{ 
        marginBottom: '32px', 
        borderLeft: `6px solid ${getFlagColor(data.overall_flag)}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 className="serif-heading" style={{ fontSize: '2.4rem', marginBottom: '8px' }}>Verification Report</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            ID: {data.report_id} | GENERATED: {new Date(data.generated_at).toLocaleString()}
          </p>
          <div style={{ 
            marginTop: '20px', 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: '12px',
            padding: '10px 20px',
            background: 'var(--bg-input)',
            borderRadius: '12px',
            fontWeight: '600',
            fontSize: '1.1rem',
            color: getFlagColor(data.overall_flag)
          }}>
            {data.overall_flag.includes('HIGH') ? <ShieldAlert size={24} /> : 
             data.overall_flag.includes('MEDIUM') ? <AlertTriangle size={24} /> : <CheckCircle size={24} />}
            {data.overall_flag}
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-outline" onClick={() => window.print()}>
            <Printer size={18} />
            Print
          </button>
          <button className="btn btn-primary">
            <Download size={18} />
            Export PDF
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '32px' }}>
        {/* Subject Info */}
        <aside>
          <div className="panel" style={{ position: 'sticky', top: '24px' }}>
            <h3 className="serif-heading" style={{ marginBottom: '20px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
               Subject Profile
            </h3>
            <div style={{ display: 'grid', gap: '16px' }}>
              <div className="info-item">
                <span className="input-label" style={{ fontSize: '0.7rem' }}>Full Identity</span>
                <p style={{ fontWeight: '600' }}>{data.subject_name}</p>
              </div>
              <div className="info-item">
                <span className="input-label" style={{ fontSize: '0.7rem' }}>Current City</span>
                <p>{subject.city}</p>
              </div>
              <div className="info-item">
                <span className="input-label" style={{ fontSize: '0.7rem' }}>Discovery Range</span>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>30-Day Persistence Policy</p>
              </div>
            </div>
          </div>
        </aside>

        {/* Findings */}
        <main>
          <div style={{ display: 'grid', gap: '24px' }}>
            {Object.entries(data.modules_run).map(([name, m]) => (
              m.ran && (
                <div key={name} className="panel" style={{ padding: '0' }}>
                  <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {m.success ? <CheckCircle size={18} color="var(--accent-green)" /> : <Info size={18} color="var(--text-muted)" />}
                      {name}
                    </h4>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Retrieved in {m.duration_sec}s
                    </span>
                  </div>

                  {m.findings && m.findings.length > 0 ? (
                    <div style={{ padding: '24px' }}>
                      {m.findings.map((f, i) => (
                        <div key={i} style={{ 
                          marginBottom: i === m.findings.length - 1 ? 0 : '20px',
                          padding: '16px',
                          background: 'var(--bg-input)',
                          borderRadius: '12px',
                          borderLeft: `4px solid ${f.priority === 'HIGH' ? 'var(--accent-crimson)' : (f.priority === 'MEDIUM' ? 'var(--accent-gold)' : 'var(--border-subtle)')}`
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: '700', letterSpacing: '0.05em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                              {f.category}
                            </span>
                            {f.priority !== 'NONE' && (
                              <span style={{ 
                                fontSize: '0.7rem', 
                                fontWeight: '700', 
                                color: f.priority === 'HIGH' ? 'var(--accent-crimson)' : 'var(--accent-gold)' 
                              }}>
                                {f.priority} PRIORITY
                              </span>
                            )}
                          </div>
                          <h5 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>{f.title}</h5>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>{f.detail}</p>
                          {f.url && (
                            <a href={f.url} target="_blank" rel="noreferrer" style={{ 
                              display: 'inline-flex', 
                              alignItems: 'center', 
                              gap: '6px', 
                              marginTop: '12px', 
                              color: 'var(--accent-gold)', 
                              fontSize: '0.85rem',
                              textDecoration: 'none',
                              fontWeight: '600'
                            }}>
                              View Source Record <ExternalLink size={14} />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      {m.skipped ? (
                        <p style={{ fontSize: '0.9rem' }}>Module skipped: {m.skip_reason}</p>
                      ) : (
                        <p style={{ fontSize: '0.9rem' }}>No significant findings detected in this data source.</p>
                      )}
                    </div>
                  )}
                </div>
              )
            ))}
          </div>

          {/* Legals */}
          <div className="panel glass" style={{ marginTop: '48px', padding: '32px', border: '1px solid var(--border-subtle)' }}>
             <h3 className="serif-heading" style={{ fontSize: '1.2rem', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
               <ShieldAlert size={20} color="var(--accent-gold)" />
               Legal Disclaimer & Restricted Use
             </h3>
             <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'grid', gap: '16px' }}>
               {Object.values(data.legal_disclaimer).map((text, i) => (
                 <p key={i}>{text}</p>
               ))}
             </div>
          </div>
        </main>
      </div>
    </div>
  );
}
