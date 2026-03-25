import React, { useState } from 'react';
import { ShieldCheck, User, Lock, Mail, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        const data = await api.login(username, password);
        const user = await api.getCurrentUser();
        onLogin(data.access_token, user);
      } else {
        await api.register(username, password);
        setIsLogin(true);
        alert('Registration successful. Please login.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in" style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      minHeight: '80vh'
    }}>
      <div className="panel" style={{ width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ 
            display: 'inline-flex', 
            padding: '12px', 
            background: 'var(--accent-gold-soft)', 
            borderRadius: '12px',
            marginBottom: '16px'
          }}>
            <ShieldCheck size={32} color="var(--accent-gold)" />
          </div>
          <h2 className="serif-heading" style={{ fontSize: '1.8rem', marginBottom: '8px' }}>
            {isLogin ? 'Welcome Back' : 'Join Inkognito'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            {isLogin ? 'Access your verification dashboard' : 'Create an account to start verifications'}
          </p>
        </div>

        {error && (
          <div style={{ 
            padding: '12px', 
            background: 'rgba(200, 42, 42, 0.1)', 
            border: '1px solid var(--accent-crimson)', 
            borderRadius: '8px',
            color: 'var(--accent-crimson)',
            fontSize: '0.85rem',
            marginBottom: '20px',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Username</label>
            <div style={{ position: 'relative' }}>
              <User size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
              <input 
                type="text" 
                placeholder="Enter your username" 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ paddingLeft: '40px' }}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
              <input 
                type="password" 
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: '40px' }}
                required
              />
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: '100%', marginTop: '8px' }} disabled={loading}>
            {loading ? <Loader2 className="spin" size={20} /> : (
              <>
                {isLogin ? 'Login' : 'Register'}
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button 
            type="button" 
            onClick={() => setIsLogin(!isLogin)}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--accent-gold)', 
              fontWeight: '600', 
              marginLeft: '8px',
              cursor: 'pointer'
            }}
          >
            {isLogin ? 'Create one' : 'Login instead'}
          </button>
        </div>
      </div>
      
      <p style={{ marginTop: '32px', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center', maxWidth: '300px' }}>
        By logging in, you agree to our terms of service and recognize that Inkognito is a data aggregation platform.
      </p>
    </div>
  );
}
