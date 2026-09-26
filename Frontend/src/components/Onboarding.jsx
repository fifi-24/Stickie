import React, { useState } from 'react';
import { API_BASE } from '../api';

const DEFAULT_INTERESTS = [
  "Trivia Nights", "Pickleball", "Coffee Catchups", "Board Games",
  "Boba Runs", "Late Night Ramen", "Vintage Thrifting", "Study Sessions"
];

// Real onboarding, three stages, every step writes to the real backend:
//   1. no verified phone yet -> ask for it, text a real magic link
//   2. verified phone, no saved profile -> name + interests -> POST /onboard/complete
//   3. profile saved, no calendar connected -> real Google OAuth redirect
export default function Onboarding({ phone, status, onComplete }) {
  const [phoneInput, setPhoneInput] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState(status?.name || '');
  const [interests, setInterests] = useState(status?.interests || []);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(Boolean(status?.exists));

  const requestLink = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${API_BASE}/onboard/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phoneInput }),
      });
      if (!res.ok) throw new Error('failed');
      setSent(true);
    } catch {
      setError('Could not send the link. Check the number and try again.');
    }
  };

  const toggleInterest = (tag) => {
    setInterests((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await fetch(`${API_BASE}/onboard/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, name, interests }),
      });
      setSaved(true);
      onComplete();
    } finally {
      setSaving(false);
    }
  };

  const connectCalendar = () => {
    window.location.href = `${API_BASE}/oauth/google/start?phone=${encodeURIComponent(phone)}`;
  };

  const card = "w-full max-w-sm bg-[#fafcfe] border border-blue-200/80 rounded-2xl p-8 shadow-[4px_6px_0px_0px_rgba(186,211,238,0.7)]";
  const wrap = "min-h-screen bg-[#edf3fa] flex flex-col justify-center items-center p-6 font-sans";
  const logo = (
    <div className="flex flex-col items-center mb-6">
      <div className="w-12 h-12 rounded-xl bg-blue-100/70 border border-blue-200 flex items-center justify-center font-mono font-bold text-blue-900 mb-3">[S]</div>
      <h1 className="text-xl font-bold text-slate-900">Stickie</h1>
      <p className="text-xs text-blue-900/60 mt-0.5">plans that stick.</p>
    </div>
  );

  // Stage 1: get + verify a phone number
  if (!phone) {
    return (
      <div className={wrap}>
        <div className={card}>
          {logo}
          {sent ? (
            <p className="text-xs text-center text-slate-600">
              Check your phone! We texted you a link — tap it to finish setting up on this device.
            </p>
          ) : (
            <form onSubmit={requestLink} className="space-y-3.5">
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">your phone number</label>
                <input
                  type="tel"
                  placeholder="+15551234567"
                  value={phoneInput}
                  onChange={(e) => setPhoneInput(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs bg-white border border-blue-200 rounded-lg outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                  required
                />
              </div>
              {error && <p className="text-[11px] text-red-600">{error}</p>}
              <button type="submit" className="w-full py-2.5 mt-2 rounded-lg text-xs font-semibold bg-blue-800 hover:bg-blue-900 text-white">
                text me a link
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // Stage 2: real profile — name + interests
  if (!saved) {
    return (
      <div className={wrap}>
        <div className={card}>
          <h2 className="text-sm font-bold text-slate-900 mb-4">Set up your profile</h2>
          <form onSubmit={saveProfile} className="space-y-3.5">
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-3.5 py-2 text-xs bg-white border border-blue-200 rounded-lg outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2">what are you into?</label>
              <div className="flex flex-wrap gap-2">
                {DEFAULT_INTERESTS.map((tag) => (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => toggleInterest(tag)}
                    className={`text-xs px-3 py-1 rounded-md ${
                      interests.includes(tag)
                        ? 'bg-blue-100/90 text-blue-950 border border-blue-300/80'
                        : 'bg-white text-slate-600 border border-dashed border-slate-300'
                    }`}
                  >
                    {interests.includes(tag) ? '✓ ' : '+ '}
                    {tag}
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" disabled={saving} className="w-full py-2.5 mt-2 rounded-lg text-xs font-semibold bg-blue-800 hover:bg-blue-900 text-white">
              {saving ? 'saving...' : 'save profile'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Stage 3: real Google Calendar connect
  return (
    <div className={wrap}>
      <div className={`${card} text-center`}>
        <h2 className="text-sm font-bold text-slate-900 mb-2">One last thing</h2>
        <p className="text-xs text-slate-600 mb-5">Connect your Google Calendar so Stickie can find real times that work for you.</p>
        <button onClick={connectCalendar} className="w-full py-2.5 rounded-lg text-xs font-semibold bg-blue-800 hover:bg-blue-900 text-white mb-3">
          connect google calendar
        </button>
        <button onClick={onComplete} className="text-[11px] font-mono text-blue-700 hover:underline">
          I just connected it — refresh
        </button>
      </div>
    </div>
  );
}
