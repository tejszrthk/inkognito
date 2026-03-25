import React, { useState, useEffect } from 'react';
import { Search, FileText, ChevronRight, Clock, User, PlusCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function Dashboard({ onNew, onViewReport }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const data = await api.getReports();
        setReports(data || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, []);

  return (
    <div className="fade-in">
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-end', 
        marginBottom: '40px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '24px'
      }}>
        <div>
          <h2 className="serif-heading" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>
            Verification Hub
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            Access and manage your archival verification reports.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onNew} style={{ padding: '14px 28px' }}>
          <PlusCircle size={20} />
          New Verification
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '100px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Loader2 className="spin" size={48} style={{ marginBottom: '16px' }} />
          <p>Retrieving your records...</p>
        </div>
      ) : error ? (
        <div className="panel" style={{ borderColor: 'var(--accent-crimson)', background: 'rgba(200, 42, 42, 0.05)' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <AlertCircle color="var(--accent-crimson)" size={24} />
            <p style={{ color: 'var(--accent-crimson)', fontWeight: '500' }}>Error: {error}</p>
          </div>
        </div>
      ) : reports.length === 0 ? (
        <div className="panel" style={{ 
          textAlign: 'center', 
          padding: '80px 40px',
          borderStyle: 'dashed',
          borderColor: 'var(--border-subtle)'
        }}>
          <div style={{ background: 'var(--bg-input)', padding: '24px', borderRadius: '50%', display: 'inline-flex', marginBottom: '24px' }}>
            <FileText size={48} color="var(--text-muted)" />
          </div>
          <h3 style={{ marginBottom: '12px', fontSize: '1.4rem' }}>No Reports Found</h3>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto 32px' }}>
            Start your first automated matrimonial verification to see it here.
          </p>
          <button className="btn btn-outline" onClick={onNew}>
            Run Your First Search
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {reports.map((report) => (
            <div 
              key={report.report_id} 
              className="panel" 
              onClick={() => onViewReport(report)}
              style={{ 
                padding: '20px 24px', 
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                <div style={{ 
                  background: 'var(--accent-gold-soft)', 
                  padding: '12px', 
                  borderRadius: '10px' 
                }}>
                  <User size={24} color="var(--accent-gold)" />
                </div>
                <div>
                  <h4 style={{ fontSize: '1.2rem', marginBottom: '4px' }}>{report.subject_name}</h4>
                  <div style={{ display: 'flex', gap: '16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} />
                      {new Date(report.generated_at).toLocaleDateString(undefined, { 
                        year: 'numeric', month: 'short', day: 'numeric' 
                      })}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Search size={14} />
                      ID: {report.report_id}
                    </span>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: 'var(--accent-gold)', fontWeight: '600', fontSize: '0.8rem', letterSpacing: '0.05em' }}>
                  VIEW ARCHIVE
                </span>
                <ChevronRight size={20} color="var(--text-muted)" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
