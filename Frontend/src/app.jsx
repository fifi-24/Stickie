import React, { useEffect, useState } from 'react';
import StickieDashboard from './components/StickieDashboard';
import Onboarding from './components/Onboarding';
import { API_BASE } from './api';

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
  // strip it from the URL so refreshing doesn't try to reuse it. A visit
  // straight back from the Google Calendar OAuth callback instead looks
  // like /?phone=... -- no verification needed there since our own
  // backend already completed and validated that round trip; this path
  // exists so the calendar step never depends on this exact browser
  // tab/origin already having the right phone in localStorage from
  // earlier in onboarding.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const phoneParam = params.get('phone');

    if (phoneParam) {
      localStorage.setItem('stickie_phone', phoneParam);
      setPhone(phoneParam);
      window.history.replaceState({}, '', '/');
      setCheckingToken(false);
      return;
    }

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
      <div className="min-h-screen bg-[#edf3fa] flex items-center justify-center text-slate-400 font-mono text-xs">
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

  return <StickieDashboard name={status.name} phone={phone} interests={status.interests} />;
}
