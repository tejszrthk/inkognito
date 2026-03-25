import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle2, Circle, AlertCircle, XCircle, Clock } from 'lucide-react';
import { api } from '../services/api';

export default function Pipeline({ jobId, onComplete, onFail }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let pollInterval;
    const poll = async () => {
      try {
        const data = await api.getJobStatus(jobId);
        setJob(data);
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          onComplete(data);
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          onFail(data);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(pollInterval);
      }
    };

    poll();
    pollInterval = setInterval(poll, 2000);
    return () => clearInterval(pollInterval);
  }, [jobId]);

  if (error) {
    return (
      <div className="panel" style={{ borderColor: 'var(--accent-crimson)', textAlign: 'center' }}>
        <AlertCircle color="var(--accent-crimson)" size={48} style={{ marginBottom: '16px' }} />
        <h3 style={{ color: 'var(--accent-crimson)' }}>Connection Interrupted</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="fade-in">
      <div style={{ textAlign: 'center', marginBottom: '48px' }}>
        <div style={{ display: 'inline-flex', padding: '16px', borderRadius: '50%', background: 'var(--accent-gold-soft)', marginBottom: '24px' }}>
          <Loader2 className="spin" size={40} color="var(--accent-gold)" />
        </div>
        <h2 className="serif-heading" style={{ fontSize: '2.2rem', marginBottom: '8px' }}>Pipeline Active</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Orchestrating search across {job.modules.length} statutory data sources.
        </p>
        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center', gap: '20px' }}>
          <div className="glass" style={{ padding: '8px 16px', borderRadius: '20px', fontSize: '0.85rem', color: 'var(--accent-gold)', border: '1px solid var(--border-gold)' }}>
             JOB ID: {jobId}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Clock size={16} />
            ELAPSED: {job.elapsed_sec}s
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '12px', maxWidth: '800px', margin: '0 auto' }}>
        {job.modules.map((mod) => (
          <div key={mod.name} className="panel" style={{ 
            padding: '16px 24px', 
            background: mod.status === 'running' ? 'var(--bg-input)' : 'var(--bg-panel)',
            borderColor: mod.status === 'running' ? 'var(--accent-gold)' : 'var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            opacity: mod.status === 'queued' ? 0.5 : 1
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {mod.status === 'running' && <Loader2 className="spin" size={20} color="var(--accent-gold)" />}
              {mod.status === 'complete' && <CheckCircle2 size={20} color="var(--accent-green)" />}
              {mod.status === 'skipped' && <AlertCircle size={20} color="var(--text-muted)" />}
              {mod.status === 'failed' && <XCircle size={20} color="var(--accent-crimson)" />}
              {mod.status === 'queued' && <Circle size={20} color="var(--text-muted)" />}
              
              <div>
                <span style={{ fontWeight: 600, fontSize: '1rem' }}>{mod.name}</span>
                {mod.skipReason && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '12px' }}>— {mod.skipReason}</span>}
                {mod.error && <span style={{ fontSize: '0.75rem', color: 'var(--accent-crimson)', marginLeft: '12px' }}>— {mod.error}</span>}
              </div>
            </div>
            
            {mod.findingsCount > 0 && (
              <div style={{ 
                background: 'var(--accent-gold)', 
                color: '#000', 
                padding: '2px 10px', 
                borderRadius: '12px', 
                fontSize: '0.75rem', 
                fontWeight: '700' 
              }}>
                {mod.findingsCount} FINDINGS
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
