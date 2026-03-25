import React, { useState } from 'react';
import { User, Phone, MapPin, Building2, Briefcase, Share2, Play, AlertTriangle } from 'lucide-react';

export default function IntakeForm({ onSubmit, runError }) {
  const [form, setForm] = useState({
    name: '',
    phone: '',
    city: '',
    employer: '',
    business: '',
    financeRole: false,
    socialUrls: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name || !form.phone || !form.city) {
      alert('Name, Phone, and City are required for verification.');
      return;
    }
    onSubmit(form);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  return (
    <div className="fade-in">
      <div style={{ marginBottom: '32px' }}>
        <h2 className="serif-heading" style={{ fontSize: '2rem', marginBottom: '8px' }}>Subject Identification</h2>
        <p style={{ color: 'var(--text-secondary)' }}>Provide the core identity markers for the automated search pipeline.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div className="input-group">
            <label className="input-label">Full Name *</label>
            <div style={{ position: 'relative' }}>
              <User size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
              <input 
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="John Doe"
                style={{ paddingLeft: '40px' }}
                required
              />
            </div>
          </div>
          
          <div className="input-group">
            <label className="input-label">Mobile Number *</label>
            <div style={{ position: 'relative' }}>
              <Phone size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
              <input 
                name="phone"
                value={form.phone}
                onChange={handleChange}
                placeholder="+91 9876543210"
                style={{ paddingLeft: '40px' }}
                required
              />
            </div>
          </div>
        </div>

        <div className="input-group">
          <label className="input-label">Current City *</label>
          <div style={{ position: 'relative' }}>
            <MapPin size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
            <input 
              name="city"
              value={form.city}
              onChange={handleChange}
              placeholder="e.g. Mumbai, Maharashtra"
              style={{ paddingLeft: '40px' }}
              required
            />
          </div>
        </div>

        <div style={{ padding: '24px', background: 'var(--bg-input)', borderRadius: '12px', marginBottom: '32px', border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ fontSize: '0.9rem', color: 'var(--accent-gold)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Optional Detail Triggers</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label className="input-label">Employer Name</label>
              <div style={{ position: 'relative' }}>
                <Building2 size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
                <input 
                  name="employer"
                  value={form.employer}
                  onChange={handleChange}
                  placeholder="e.g. Google India"
                  style={{ paddingLeft: '40px' }}
                />
              </div>
            </div>
            
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label className="input-label">Business Name</label>
              <div style={{ position: 'relative' }}>
                <Briefcase size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
                <input 
                  name="business"
                  value={form.business}
                  onChange={handleChange}
                  placeholder="e.g. XYZ Enterprises"
                  style={{ paddingLeft: '40px' }}
                />
              </div>
            </div>
          </div>

          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input 
              type="checkbox"
              name="financeRole"
              checked={form.financeRole}
              onChange={handleChange}
              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-gold)' }}
            />
            <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Subject holds a finance-sensitive role (triggers SEBI Enforcement check)
            </label>
          </div>
        </div>

        <div className="input-group">
          <label className="input-label">Social Media URLs (Comma separated)</label>
          <div style={{ position: 'relative' }}>
            <Share2 size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
            <input 
              name="socialUrls"
              value={form.socialUrls}
              onChange={handleChange}
              placeholder="LinkedIn profile, Instagram handle, etc."
              style={{ paddingLeft: '40px' }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
            Help our AI cross-verify identity by providing known social handles.
          </p>
        </div>

        {runError && (
          <div className="panel" style={{ borderColor: 'var(--accent-crimson)', background: 'rgba(200, 42, 42, 0.05)', marginBottom: '24px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <AlertTriangle color="var(--accent-crimson)" size={20} />
              <p style={{ color: 'var(--accent-crimson)', fontSize: '0.9rem' }}>{runError}</p>
            </div>
          </div>
        )}

        <button className="btn btn-primary" style={{ width: '100%', padding: '16px' }}>
          <Play size={20} fill="currentColor" />
          Initialize Search Pipeline
        </button>
      </form>
    </div>
  );
}
