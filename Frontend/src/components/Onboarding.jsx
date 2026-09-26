import React, { useRef, useState } from 'react';
import { API_BASE } from '../api';

// Design tokens matching StickieDashboard.jsx
const CORK_BG = '#E7DEC8';       // Corkboard / craft paper canvas
const DESK_BG = '#FBF8F1';       // Desk card background
const POSTIT_YELLOW = '#FEF9C3'; // Classic yellow sticky
const POSTIT_YELLOW_TAPE = 'rgba(234, 179, 8, 0.22)';
const POSTIT_BLUE = '#E0F2FE';   // Pastel blue sticky
const INK = '#2B2620';
const MUTED = '#716553';
const STICKY_SHADOW = '0 1px 3px rgba(0,0,0,0.06), 2px 7px 15px -3px rgba(60, 45, 10, 0.12)';

const labeled = {
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: '0.07em',
  fontFamily: 'monospace',
  color: MUTED,
  fontWeight: 700,
};

function Logo({ size = 48 }) {
  return (
    <div
      style={{
        background: '#FACC15',
        width: size,
        height: size,
        transform: 'rotate(-0.8deg)',
      }}
      className="flex items-center justify-center shadow-xs rounded-xs overflow-hidden"
    >
      <img src="/stickieLogo.png" alt="Stickie Logo" className="w-full h-full object-contain" />
    </div>
  );
}

export default function Onboarding({ phone, status, onComplete, onVerified, onSkipCalendar }) {
  const [name, setName] = useState(status?.name || '');
  const [phoneInput, setPhoneInput] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [digits, setDigits] = useState(['', '', '', '']);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const inputRefs = [useRef(), useRef(), useRef(), useRef()];

  const formatE164 = (raw) => {
    const cleaned = raw.replace(/\D/g, '');
    if (cleaned.startsWith('1') && cleaned.length === 11) {
      return `+${cleaned}`;
    }
    return `+1${cleaned}`;
  };

  const sendCode = async (e) => {
    e.preventDefault();
    setError('');
    if (!name.trim() || !phoneInput.trim()) return;
    setSending(true);

    const formatted = formatE164(phoneInput);

    try {
      const res = await fetch(`${API_BASE}/onboard/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: formatted }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'failed');
      }
      setCodeSent(true);
      setDigits(['', '', '', '']);
      setTimeout(() => inputRefs[0].current?.focus(), 50);
    } catch (err) {
      setError(err.message || 'Could not send a code. Check the number and try again.');
    } finally {
      setSending(false);
    }
  };

  const submitCode = async (fullCode) => {
    setError('');
    const formatted = formatE164(phoneInput);
    try {
      const res = await fetch(`${API_BASE}/onboard/verify-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: formatted, name, code: fullCode }),
      });
      if (!res.ok) throw new Error('failed');
      onVerified(formatted);
    } catch {
      setError('Wrong code — try again.');
      setDigits(['', '', '', '']);
      inputRefs[0].current?.focus();
    }
  };

  const handleDigitChange = (i, value) => {
    const clean = value.replace(/[^0-9]/g, '').slice(-1);
    const next = [...digits];
    next[i] = clean;
    setDigits(next);
    if (clean && i < 3) inputRefs[i + 1].current?.focus();
    if (next.every((d) => d !== '')) submitCode(next.join(''));
  };

  const handleDigitKeyDown = (i, e) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) inputRefs[i - 1].current?.focus();
  };

  // Stage 1/2: not verified yet -- login form, then code entry.
  if (!phone) {
    return (
      <div className="min-h-screen text-[#2b2620] flex flex-col items-center justify-center p-4 font-sans" style={{ background: CORK_BG }}>
        <div
          className="w-full max-w-sm rounded-xs border border-[#d8cdb4] shadow-2xl p-6 relative"
          style={{ background: DESK_BG }}
        >
          {/* Header & Logo */}
          <div className="flex flex-col items-center mb-6">
            <Logo size={48} />
            <h1 className="font-serif text-2xl font-bold mt-3" style={{ color: INK }}>
              Stickie
            </h1>
            <p className="text-xs font-mono tracking-wide mt-1" style={{ color: MUTED }}>
              Glue of your social life!
            </p>
          </div>

          {!codeSent ? (
            /* Yellow Sticky Note for Sign In */
            <div
              className="p-5 rounded-xs relative transition duration-150"
              style={{
                background: POSTIT_YELLOW,
                boxShadow: STICKY_SHADOW,
                border: '1px solid #FDE047',
                transform: 'rotate(-0.6deg)',
              }}
            >
              {/* Tape strip */}
              <div
                className="h-3 absolute -top-1.5 left-1/4 right-1/4 rounded-xs shadow-2xs backdrop-blur-xs"
                style={{ background: POSTIT_YELLOW_TAPE }}
              />

              <div className="mb-3" style={labeled}>
                Log In / Register
              </div>

              <form onSubmit={sendCode} className="space-y-3.5">
                <div>
                  <label className="block mb-1 text-[11px] font-mono text-amber-950 font-medium">
                    Full Name
                  </label>
                  <input
                    type="text"
                    placeholder="John Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-white/90 border border-yellow-400/60 rounded-xs outline-none focus:bg-white text-stone-900"
                    required
                  />
                </div>

                <div>
                  <label className="block mb-1 text-[11px] font-mono text-amber-950 font-medium">
                    Phone Number
                  </label>
                  <div className="flex items-center gap-1.5 bg-white/90 border border-yellow-400/60 rounded-xs px-3 py-2 focus-within:bg-white">
                    <span className="text-xs font-mono font-bold text-amber-900">+1</span>
                    <input
                      type="tel"
                      placeholder="(415) 555-0182"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      className="flex-1 text-sm bg-transparent outline-none text-stone-900"
                      required
                    />
                  </div>
                </div>

                {error && <p className="text-[11px] font-mono text-red-600">{error}</p>}

                <button
                  type="submit"
                  disabled={sending}
                  className="w-full py-2.5 mt-2 rounded-xs text-xs font-mono font-bold text-stone-900 bg-amber-400 hover:bg-amber-300 border border-amber-500/50 shadow-xs active:scale-[0.98] transition cursor-pointer"
                >
                  {sending ? 'Sending...' : 'Send Verification Code'}
                </button>

                <p className="text-[10px] font-mono text-stone-500 text-center pt-2 leading-tight">
                  By continuing, you agree to Stickie's terms &amp; auto-scheduling.
                </p>
              </form>
            </div>
          ) : (
            /* Yellow Sticky Note for Verification Digits */
            <div
              className="p-5 rounded-xs relative transition duration-150"
              style={{
                background: POSTIT_YELLOW,
                boxShadow: STICKY_SHADOW,
                border: '1px solid #FDE047',
                transform: 'rotate(0.5deg)',
              }}
            >
              <div
                className="h-3 absolute -top-1.5 left-1/4 right-1/4 rounded-xs shadow-2xs backdrop-blur-xs"
                style={{ background: POSTIT_YELLOW_TAPE }}
              />

              <div className="mb-2" style={labeled}>
                Verification Code
              </div>
              <p className="text-xs font-mono text-stone-600 mb-4">
                Enter the 4-digit code sent to your phone:
              </p>

              <div className="flex justify-center gap-2.5 mb-4">
                {digits.map((d, i) => (
                  <input
                    key={i}
                    ref={inputRefs[i]}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={d}
                    onChange={(e) => handleDigitChange(i, e.target.value)}
                    onKeyDown={(e) => handleDigitKeyDown(i, e)}
                    className="w-12 h-14 text-center text-xl font-mono font-bold bg-white/90 border border-yellow-400 rounded-xs outline-none focus:bg-white text-stone-900 shadow-2xs"
                  />
                ))}
              </div>

              {error && <p className="text-[11px] font-mono text-red-600 text-center mb-3">{error}</p>}

              <div className="text-center">
                <button
                  type="button"
                  onClick={sendCode}
                  className="text-xs font-mono font-bold text-amber-900 underline hover:text-amber-700 cursor-pointer"
                >
                  Didn't receive a code? Resend
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Stage 3: verified, no calendar connected yet -- Pastel Blue Sticky Card
  const connectCalendar = () => {
    window.location.href = `${API_BASE}/oauth/google/start?phone=${encodeURIComponent(phone)}`;
  };

  return (
    <div className="min-h-screen text-[#2b2620] flex flex-col items-center justify-center p-4 font-sans" style={{ background: CORK_BG }}>
      <div
        className="w-full max-w-sm rounded-xs border border-[#d8cdb4] shadow-2xl p-6 relative"
        style={{ background: DESK_BG }}
      >
        <div className="flex flex-col items-center mb-5">
          <Logo size={44} />
        </div>

        <div
          className="p-5 rounded-xs relative text-center"
          style={{
            background: POSTIT_BLUE,
            boxShadow: STICKY_SHADOW,
            border: '1px solid #BAE6FD',
            transform: 'rotate(-0.5deg)',
          }}
        >
          {/* Tape strip */}
          <div className="h-2 absolute top-0 left-0 right-0 rounded-t-xs bg-blue-300/30" />

          <div className="mb-2" style={{ ...labeled, color: '#0369A1' }}>
            Calendar Integration
          </div>

          <h2 className="font-serif text-lg font-bold text-sky-950 mb-2">
            Sync Your Google Calendar
          </h2>

          <p className="text-xs font-mono text-slate-600 mb-5 leading-relaxed">
            Stickie cross-references free time across connected schedules so hangouts happen without groupchat debate.
          </p>

          <button
            onClick={connectCalendar}
            className="w-full py-2.5 rounded-xs text-xs font-mono font-bold text-sky-900 bg-white border border-sky-300 shadow-xs hover:bg-sky-50 active:scale-[0.98] transition cursor-pointer mb-3"
          >
            Connect Google Calendar
          </button>

          <div className="flex items-center justify-center gap-4 pt-1">
            <button
              onClick={onComplete}
              className="text-[11px] font-mono font-semibold text-slate-600 hover:text-slate-900 underline cursor-pointer"
            >
              Connected — Refresh
            </button>
            <span className="text-slate-400 font-mono text-xs">•</span>
            <button
              onClick={onSkipCalendar}
              className="text-[11px] font-mono text-slate-500 hover:text-slate-800 underline cursor-pointer"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}