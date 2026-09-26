import React, { useEffect, useState } from 'react';
import StickieDashboard from './components/StickieDashboard';
import Onboarding from './components/Onboarding';

const API_BASE = 'http://localhost:8000';

// The site's front door: every visitor either has a verified phone number
// with a real, completed profile (name + interests + Google Calendar) —
// in which case they see the real dashboard — or they don't, in which
// case Onboarding is the first and only thing they see, no matter what
// URL they land on.
export default function App() {
  const [phone, setPhone] = useState(() => localStorage.getItem('stickie_phone') || '');
  const [status, setStatus] = useState(null);
  const [checkingToken, setCheckingToken] = useState(true);

  // A magic-link visit looks like /?token=... — verify it once, then
  // strip it from the URL so refreshing doesn't try to reuse it.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (!token) {
      setCheckingToken(false);
      return;
    }
    fetch(`${API_BASE}/onboard/verify?token=${encodeURIComponent(token)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => {
        localStorage.setItem('stickie_phone', data.phone);
        setPhone(data.phone);
        window.history.replaceState({}, '', '/');
      })
      .catch(() => {})
      .finally(() => setCheckingToken(false));
  }, []);

  const refreshStatus = () => {
    if (!phone) {
      setStatus({ exists: false });
      return;
    }
    fetch(`${API_BASE}/users/status?phone=${encodeURIComponent(phone)}`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ exists: false }));
  };

  useEffect(() => {
    if (checkingToken) return;
    refreshStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phone, checkingToken]);

  if (checkingToken || status === null) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400 font-mono text-xs">
        loading...
      </div>
    );
  }

  const fullyOnboarded = status.exists && status.has_calendar;

  if (!fullyOnboarded) {
    return (
      <Onboarding
        phone={phone}
        status={status}
        onComplete={refreshStatus}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <StickieDashboard />
    </div>
  );
}
