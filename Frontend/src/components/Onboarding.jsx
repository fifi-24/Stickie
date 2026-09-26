import React, { useRef, useState } from 'react';
import { API_BASE } from '../api';

// Real onboarding: name + phone together -> real 4-digit SMS code ->
// (optional) real Google Calendar connect. Every step writes to the
// real backend; nothing here is mocked. Dark page / cream card / gold
// accent to match the agreed design -- shared by every screen here and
// by the dashboard's own header badge.
const PAGE_BG = '#171512';
const CARD_BG = '#FAF1DC';
const ACCENT = '#F0C94C';

function Logo({ cutoutColor }) {
  return (
    <div
      className="w-14 h-14 rounded-2xl relative overflow-hidden shadow-md"
      style={{ background: ACCENT }}
    >
      <div
        className="absolute -top-3 -right-3 w-7 h-7 rotate-45"
        style={{ background: cutoutColor }}
      />
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

  const wrap = 'min-h-screen flex flex-col justify-center items-center p-6 font-sans';
  const wrapStyle = { background: PAGE_BG };
  const card =
    'w-full max-w-sm rounded-3xl p-8 shadow-2xl';
  const cardStyle = { background: CARD_BG };

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
      <div className={wrap} style={wrapStyle}>
        <div className={card} style={cardStyle}>
          <div className="flex flex-col items-center mb-7">
            <Logo cutoutColor={PAGE_BG} />
            <h1 className="font-serif-stickie text-3xl font-bold text-[#2b2620] mt-4">Stickie</h1>
            <p className="text-xs text-[#7a6f5d] mt-1">Glue of your social life!</p>
          </div>

          {!codeSent ? (
            <>
              <h2 className="font-serif-stickie text-xl font-bold text-[#2b2620] mb-4">Log in</h2>
              <form onSubmit={sendCode} className="space-y-4">
                <div>
                  <label className="block text-[10px] font-mono uppercase tracking-wider text-[#8a7d68] mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm bg-white/70 border border-[#e6d9b8] rounded-xl outline-none focus:border-[#F0C94C]"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono uppercase tracking-wider text-[#8a7d68] mb-1">
                    Phone Number
                  </label>
                  <div className="flex items-center gap-2 bg-white/70 border border-[#e6d9b8] rounded-xl px-3.5 py-2.5 focus-within:border-[#F0C94C]">
                    <span className="text-sm text-[#8a7d68]">+1</span>
                    <input
                      type="tel"
                      placeholder="(415) 555-0182"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      className="flex-1 text-sm bg-transparent outline-none"
                      required
                    />
                  </div>
                </div>
                {error && <p className="text-[11px] text-red-600">{error}</p>}
                <button
                  type="submit"
                  disabled={sending}
                  className="w-full py-3 mt-2 rounded-xl text-sm font-semibold text-[#2b2620] shadow-sm active:scale-[0.98] transition"
                  style={{ background: ACCENT }}
                >
                  {sending ? 'sending...' : 'Send Verification Code'}
                </button>
                <p className="text-[10px] text-[#8a7d68] text-center pt-1">
                  By continuing, you agree to our Terms of Service and Privacy Policy.
                </p>
              </form>
            </>
          ) : (
            <>
              <h2 className="font-serif-stickie text-xl font-bold text-[#2b2620] mb-1">Verification</h2>
              <p className="text-[10px] font-mono uppercase tracking-wider text-[#8a7d68] mb-4">Enter Code</p>
              <div className="flex justify-center gap-3 mb-4">
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
                    className="w-12 h-14 text-center text-xl font-bold bg-white/70 border border-[#e6d9b8] rounded-xl outline-none focus:border-[#F0C94C]"
                  />
                ))}
              </div>
              {error && <p className="text-[11px] text-red-600 text-center mb-2">{error}</p>}
              <p className="text-xs text-[#8a7d68] text-center">
                Didn't receive a code?{' '}
                <button onClick={sendCode} className="font-semibold text-[#2b2620] hover:underline">
                  Resend
                </button>
              </p>
            </>
          )}
        </div>
      </div>
    );
  }

  // Stage 3: verified, no calendar connected yet -- optional interstitial.
  const connectCalendar = () => {
    window.location.href = `${API_BASE}/oauth/google/start?phone=${encodeURIComponent(phone)}`;
  };

  return (
    <div className={wrap} style={wrapStyle}>
      <div className={`${card} text-center`} style={cardStyle}>
        <div className="flex justify-center mb-6">
          <Logo cutoutColor={CARD_BG} />
        </div>
        <h2 className="font-serif-stickie text-xl font-bold text-[#2b2620] mb-2">Sync Your Calendar</h2>
        <p className="text-xs text-[#7a6f5d] mb-6 leading-relaxed">
          Stickie needs calendar access to automatically find overlapping free time when your group plans things.
        </p>
        <button
          onClick={connectCalendar}
          className="w-full py-3 rounded-xl text-sm font-semibold text-[#2b2620] shadow-sm active:scale-[0.98] transition mb-3"
          style={{ background: ACCENT }}
        >
          Connect Google Calendar
        </button>
        <button onClick={onComplete} className="text-[11px] font-mono text-[#8a7d68] hover:underline mr-3">
          I just connected it — refresh
        </button>
        <button onClick={onSkipCalendar} className="text-[11px] font-mono text-[#8a7d68] hover:underline">
          Skip for now
        </button>
      </div>
    </div>
  );
}
