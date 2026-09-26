import React, { useEffect, useState } from 'react';
import { API_BASE } from '../api';

const DEFAULT_INTERESTS = [
  "Trivia Nights",
  "Pickleball",
  "Coffee Catchups",
  "Board Games",
  "Boba Runs",
  "Late Night Ramen",
  "Vintage Thrifting",
  "Study Sessions"
];

const PAST_HANGOUTS = [
  { id: 101, month: "Sept", title: "Midtown Trivia Run", date: "Sept 24", attendees: "Anvi, Bhaumi", venue: "Midtown Moon", note: "Won 2nd place! Next round is Tuesday." },
  { id: 102, month: "Sept", title: "Westside Pickleball", date: "Sept 18", attendees: "Ellie, Bhaumi", venue: "Westside Courts", note: "3 sets played under the lights." },
  { id: 103, month: "Sept", title: "Spontaneous Coffee Spark", date: "Sept 12", attendees: "Bhaumi", venue: "Student Center Lounge", note: "15-min iced matcha break between classes." },
  { id: 104, month: "Aug", title: "Late Night Boba Run", date: "Aug 04", attendees: "Sophie, Anvi", venue: "Sweet Hut Bakery", note: "Crossover catchup session!" },
];

// Design tokens
const CORK_BG = '#E7DEC8';       // Corkboard / craft paper canvas
const DESK_BG = '#FBF8F1';
const POSTIT_YELLOW = '#FEF9C3'; // Classic yellow sticky
const POSTIT_YELLOW_TAPE = 'rgba(234, 179, 8, 0.22)';
const POSTIT_PINK = '#FCE7F3';   // Pastel pink sticky
const POSTIT_BLUE = '#E0F2FE';   // Pastel blue sticky
const POSTIT_GREEN = '#DCFCE7';  // Soft mint sticky
const INK = '#2B2620';
const MUTED = '#716553';

const CADENCE_DAYS = { Weekly: 7, 'Bi-weekly': 14, Monthly: 30 };
const DAYS_TO_CADENCE = { 7: 'Weekly', 14: 'Bi-weekly', 30: 'Monthly' };

const STICKY_SHADOW = '0 1px 3px rgba(0,0,0,0.06), 2px 7px 15px -3px rgba(60, 45, 10, 0.12)';

function Logo({ size = 28, cutoutColor = DESK_BG, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-sm relative overflow-hidden shadow-sm shrink-0 transition-transform active:scale-95 ${onClick ? 'cursor-pointer' : ''}`}
      style={{ background: '#FACC15', width: size, height: size, boxShadow: '1px 2px 5px rgba(0,0,0,0.15)' }}
    >
      <div
        className="absolute rotate-45"
        style={{
          background: cutoutColor,
          width: size * 0.55,
          height: size * 0.55,
          top: -size * 0.28,
          right: -size * 0.28,
        }}
      />
    </div>
  );
}

function groupByMonth(events) {
  const groups = [];
  for (const event of events) {
    const last = groups[groups.length - 1];
    if (last && last.month === event.month) last.events.push(event);
    else groups.push({ month: event.month, events: [event] });
  }
  return groups;
}

export default function StickieDashboard({ name = '', phone: realPhone = '', interests = [], nudgeThresholdDays = null }) {
  const [fullName, setFullName] = useState(name || 'Stickie User');
  const [pronouns, setPronouns] = useState('they/them');
  const [phone, setPhone] = useState(realPhone || '');
  const [cadence, setCadence] = useState(DAYS_TO_CADENCE[nudgeThresholdDays] || 'Monthly');
  const [presence, setPresence] = useState('Active');
  const [hasCalendar, setHasCalendar] = useState(null);

  const [view, setView] = useState('dashboard');
  const [activeTab, setActiveTab] = useState('friends');
  const [statusBanner, setStatusBanner] = useState('');

  const [selectedInterests, setSelectedInterests] = useState(
    interests.length ? interests : ['Trivia Nights', 'Coffee Catchups', 'Pickleball']
  );
  const [customTagInput, setCustomTagInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const [crew, setCrew] = useState({ mutual: [], solo: [] });
  const [crewLoading, setCrewLoading] = useState(false);
  const [newFriendName, setNewFriendName] = useState('');
  const [newFriendPhone, setNewFriendPhone] = useState('');
  const [showAddFriend, setShowAddFriend] = useState(false);

  useEffect(() => {
    if (realPhone) setPhone(realPhone);
  }, [realPhone]);

  const sortOverdueFirst = (list) =>
    [...list].sort((a, b) => (b.overdue ? 1 : 0) - (a.overdue ? 1 : 0));

  const fetchCrew = () => {
    if (!phone) return;
    setCrewLoading(true);
    fetch(`${API_BASE}/crew?phone=${encodeURIComponent(phone)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setCrew({
        mutual: sortOverdueFirst(data.mutual || []),
        solo: sortOverdueFirst(data.solo || []),
        nudge_threshold_days: data.nudge_threshold_days,
      }))
      .catch((err) => console.warn('crew fetch error:', err))
      .finally(() => setCrewLoading(false));
  };

  useEffect(() => {
    if (activeTab === 'friends' && phone) fetchCrew();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, phone]);

  useEffect(() => {
    if (!phone) return;
    fetch(`${API_BASE}/users/status?phone=${encodeURIComponent(phone)}`)
      .then((r) => r.json())
      .then((data) => setHasCalendar(Boolean(data.has_calendar)))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phone]);

  const toggleInterest = (tag) => {
    setSelectedInterests(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const handleAddCustomInterest = (e) => {
    e.preventDefault();
    const clean = customTagInput.trim();
    if (clean && !selectedInterests.includes(clean)) {
      setSelectedInterests(prev => [...prev, clean]);
      setCustomTagInput('');
      setShowCustomInput(false);
    }
  };

  const handleAddFriend = async (e) => {
    e.preventDefault();
    if (!newFriendName.trim() || !newFriendPhone.trim()) return;
    await fetch(`${API_BASE}/contacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_phone: phone, name: newFriendName.trim(), phone: newFriendPhone.trim() }),
    });
    setNewFriendName('');
    setNewFriendPhone('');
    setShowAddFriend(false);
    fetchCrew();
  };

  const nudgeOne = async (kind, key) => {
    setStatusBanner('📌 Sending nudge...');
    try {
      const res = await fetch(`${API_BASE}/api/nudge-one`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, kind, key }),
      });
      setStatusBanner(res.ok ? '✓ Nudge delivered' : 'Could not send that nudge');
    } catch (err) {
      setStatusBanner('Nudge failed: ' + err.message);
    }
    setTimeout(() => setStatusBanner(''), 3000);
    fetchCrew();
  };

  const updateContactCadence = async (contactId, cadenceLabel) => {
    await fetch(`${API_BASE}/contacts/${contactId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_phone: phone, cadence_days: CADENCE_DAYS[cadenceLabel] }),
    });
    fetchCrew();
  };

  const triggerProximitySpark = async () => {
    // 1. Guard check (case-insensitive)
    if (!presence || presence.toLowerCase() !== 'active') {
      setStatusBanner(`⚠️ Proximity muted: your status is set to "${presence}".`);
      setTimeout(() => setStatusBanner(''), 3500);
      return;
    }

    if (!phone) {
      setStatusBanner('⚠️ Error: No phone number configured.');
      setTimeout(() => setStatusBanner(''), 3500);
      return;
    }

    setStatusBanner('⚡️ Dispatching proximity ping...');
    try {
      const res = await fetch(`${API_BASE}/api/simulate-proximity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_a_name: fullName.split(' ')[0] || 'Sophie',
          user_b_name: 'Bhaumi',
          target_phone: phone,
          presence: presence, // Passes "Active"
          location_name: 'Student Center Coffee Lounge'
        })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }

      const data = await res.json();
      if (data.skipped) {
        setStatusBanner(data.message || '⚠️ Proximity spark skipped.');
      } else {
        setStatusBanner('✓ Ping delivered to your device.');
      }
      setTimeout(() => setStatusBanner(''), 4500);
    } catch (err) {
      console.error('Proximity error:', err);
      setStatusBanner('Trigger failed: ' + err.message);
      setTimeout(() => setStatusBanner(''), 4000);
    }
  };

  const updateCadence = async (value) => {
    setCadence(value);
    try {
      await fetch(`${API_BASE}/users/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, nudge_threshold_days: CADENCE_DAYS[value] }),
      });
    } catch {
      // best-effort
    }
  };

  const connectCalendar = () => {
    window.location.href = `${API_BASE}/oauth/google/start?phone=${encodeURIComponent(phone)}`;
  };

  const labeled = { fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.07em', fontFamily: 'monospace', color: MUTED, fontWeight: 700 };

  // ============================================================
  // SETTINGS (Corkboard Sticky Layout)
  // ============================================================
  if (view === 'settings') {
    return (
      <div className="min-h-screen text-[#2b2620] flex flex-col items-center font-sans" style={{ background: CORK_BG }}>
        <div className="w-full max-w-md min-h-screen flex flex-col border-x border-[#d8cdb4]" style={{ background: DESK_BG }}>
          <header className="px-5 py-4 flex items-center justify-between border-b border-[#ebdcb9]">
            <div className="flex items-center gap-3">
              <Logo size={30} cutoutColor={DESK_BG} onClick={() => setView('dashboard')} />
              <h1 className="font-serif text-lg font-bold" style={{ color: INK }}>Settings</h1>
            </div>
            <button
              onClick={() => setView('dashboard')}
              className="text-xs font-mono px-3 py-1 rounded bg-[#FEF9C3] border border-[#EAB308]/40 shadow-xs hover:bg-[#FEF08A]"
            >
              ← back
            </button>
          </header>

          <main className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
            
            {/* Sticky Card 1: Profile (Yellow) */}
            <div
              className="p-5 rounded-sm relative transition hover:rotate-0"
              style={{
                background: POSTIT_YELLOW,
                boxShadow: STICKY_SHADOW,
                transform: 'rotate(-0.4deg)',
              }}
            >
              <div className="h-2 absolute top-0 left-0 right-0 rounded-t-sm" style={{ background: POSTIT_YELLOW_TAPE }} />
              <div className="mb-3" style={labeled}>📌 Profile &amp; Account</div>
              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-[11px] font-mono">Display Name</label>
                  <input
                    type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm bg-white/90 border border-yellow-400/50 rounded-xs outline-none focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block mb-1 text-[11px] font-mono">Phone Number</label>
                  <input
                    type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm bg-white/90 border border-yellow-400/50 rounded-xs outline-none focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block mb-1 text-[11px] font-mono">Pronouns</label>
                  <select
                    value={pronouns} onChange={(e) => setPronouns(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm bg-white/90 border border-yellow-400/50 rounded-xs outline-none focus:bg-white"
                  >
                    <option value="they/them">they/them</option>
                    <option value="she/her">she/her</option>
                    <option value="he/him">he/him</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Sticky Card 2: Scheduling & Spontaneous (Pink) */}
            <div
              className="p-5 rounded-sm relative transition hover:rotate-0"
              style={{
                background: POSTIT_PINK,
                boxShadow: STICKY_SHADOW,
                transform: 'rotate(0.5deg)',
              }}
            >
              <div className="h-2 absolute top-0 left-0 right-0 rounded-t-sm bg-pink-300/30" />
              <div className="mb-3" style={{ ...labeled, color: '#831843' }}>📌 Availability &amp; Cadence</div>
              <div className="space-y-3">
                <div>
                  <label className="block mb-1 text-[11px] font-mono">Check in with crew every</label>
                  <select
                    value={cadence} onChange={(e) => updateCadence(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm bg-white/90 border border-pink-300 rounded-xs outline-none"
                  >
                    <option value="Weekly">1 week</option>
                    <option value="Bi-weekly">2 weeks</option>
                    <option value="Monthly">1 month</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 text-[11px] font-mono">Spontaneous Mode</label>
                  <div className="flex gap-2">
                    {['Active', 'Busy', 'Off'].map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setPresence(mode)}
                        className="flex-1 py-1.5 text-xs font-mono rounded-xs border shadow-xs transition"
                        style={
                          presence === mode
                            ? { background: '#F472B6', color: '#fff', borderColor: '#DB2777', fontWeight: 700 }
                            : { background: '#fff', color: INK, borderColor: '#FBCFE8' }
                        }
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Sticky Card 3: Interests Tags (Green) */}
            <div
              className="p-5 rounded-sm relative transition hover:rotate-0"
              style={{
                background: POSTIT_GREEN,
                boxShadow: STICKY_SHADOW,
                transform: 'rotate(-0.3deg)',
              }}
            >
              <div className="h-2 absolute top-0 left-0 right-0 rounded-t-sm bg-emerald-400/20" />
              <div className="flex items-center justify-between mb-2">
                <span style={{ ...labeled, color: '#065F46' }}>📌 Interests</span>
                <span style={labeled}>{selectedInterests.length} tagged</span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {DEFAULT_INTERESTS.map((tag) => {
                  const isSelected = selectedInterests.includes(tag);
                  return (
                    <button
                      key={tag}
                      onClick={() => toggleInterest(tag)}
                      className="text-xs px-2.5 py-1 rounded-xs font-medium transition shadow-2xs"
                      style={
                        isSelected
                          ? { background: '#10B981', color: '#fff', border: '1px solid #059669' }
                          : { background: '#fff', color: INK, border: '1px solid #A7F3D0' }
                      }
                    >
                      {isSelected ? '✓ ' : '+ '}{tag}
                    </button>
                  );
                })}
                {selectedInterests.filter((t) => !DEFAULT_INTERESTS.includes(t)).map((tag) => (
                  <button
                    key={tag}
                    onClick={() => toggleInterest(tag)}
                    className="text-xs px-2.5 py-1 rounded-xs font-medium bg-[#10B981] text-white border border-[#059669]"
                  >
                    ✓ {tag}
                  </button>
                ))}
                {!showCustomInput ? (
                  <button
                    type="button"
                    onClick={() => setShowCustomInput(true)}
                    className="text-xs px-2.5 py-1 rounded-xs border border-dashed border-emerald-600 bg-white/70"
                  >
                    + custom note
                  </button>
                ) : (
                  <div className="flex items-center gap-1">
                    <input
                      type="text" autoFocus placeholder="new interest"
                      value={customTagInput}
                      onChange={(e) => setCustomTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddCustomInterest(e);
                        if (e.key === 'Escape') setShowCustomInput(false);
                      }}
                      className="px-2 py-0.5 text-xs bg-white border border-emerald-400 rounded-xs outline-none"
                    />
                    <button onClick={handleAddCustomInterest} className="text-xs px-2 py-0.5 rounded-xs font-bold bg-[#10B981] text-white">
                      add
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Sticky Card 4: Connected Services (Blue) */}
            <div
              className="p-4 rounded-sm relative transition hover:rotate-0 flex items-center justify-between"
              style={{
                background: POSTIT_BLUE,
                boxShadow: STICKY_SHADOW,
                transform: 'rotate(0.4deg)',
              }}
            >
              <div className="h-2 absolute top-0 left-0 right-0 rounded-t-sm bg-blue-300/30" />
              <div>
                <div className="text-xs font-bold mt-1" style={{ color: '#0369A1' }}>Google Calendar</div>
                <div className="text-[11px] font-mono text-slate-600">
                  {hasCalendar === null ? 'checking...' : hasCalendar ? 'Connected (syncing live)' : 'Not connected'}
                </div>
              </div>
              <button
                onClick={connectCalendar}
                className="text-[11px] font-mono px-3 py-1 rounded-xs border font-semibold bg-white text-sky-800 border-sky-300 shadow-xs hover:bg-sky-50"
              >
                {hasCalendar ? 'reconnect' : 'connect'}
              </button>
            </div>

            {/* Text Commands helper */}
            <div className="space-y-2 pt-2">
              <div style={labeled}>Sticky Quick Commands</div>
              {[
                { cmd: '/website', desc: 'Auto-logs into your dashboard.' },
                { cmd: '/plan <activity>', desc: 'Launches group planning prompt.' },
                { cmd: '/nudge', desc: 'Triggers overdue check-ins.' },
              ].map((c) => (
                <div key={c.cmd} className="rounded-xs px-3 py-2 border border-stone-300 bg-white/80 shadow-2xs">
                  <span className="text-xs font-mono font-bold text-amber-800">{c.cmd}</span>
                  <span className="text-[11px] ml-2 text-stone-600">— {c.desc}</span>
                </div>
              ))}
            </div>

            {/* Debug trigger */}
            <button
              onClick={triggerProximitySpark}
              className="w-full py-2 rounded-xs text-xs font-mono font-medium transition active:scale-[0.99] border border-stone-400 bg-stone-700 text-white shadow-xs"
            >
              ⚡️ Fire Proximity Spark (Flow C demo)
            </button>

            <button
              onClick={() => { localStorage.removeItem('stickie_phone'); window.location.href = '/'; }}
              className="w-full py-2 rounded-xs text-xs font-mono font-semibold border border-stone-300 text-stone-700 bg-white hover:bg-stone-50"
            >
              Sign Out
            </button>
          </main>
        </div>
      </div>
    );
  }

  // ============================================================
  // DASHBOARD VIEW
  // ============================================================
  return (
    <div className="min-h-screen text-[#2b2620] flex flex-col items-center font-sans" style={{ background: CORK_BG }}>
      <div className="w-full max-w-md min-h-screen flex flex-col justify-between border-x border-[#d8cdb4] shadow-2xl relative" style={{ background: DESK_BG }}>

        {/* TOP BAR */}
        <header className="sticky top-0 z-40 backdrop-blur-md px-5 py-3.5 flex items-center justify-between border-b border-[#e9dcbd] bg-[#fbf8f1]/90">
          <Logo size={28} cutoutColor={DESK_BG} />
          <div className="text-xs font-mono uppercase tracking-widest font-bold opacity-40">stickie desk</div>
          <button
            onClick={() => setView('settings')}
            className="w-7 h-7 flex flex-col justify-center items-end gap-1 px-0.5 cursor-pointer opacity-70 hover:opacity-100"
            aria-label="Settings"
          >
            <span className="w-4 h-[1.5px] rounded-full bg-stone-800" />
            <span className="w-3.5 h-[1.5px] rounded-full bg-stone-800" />
            <span className="w-2.5 h-[1.5px] rounded-full bg-stone-800" />
          </button>
        </header>

        {statusBanner && (
          <div className="mx-4 mt-3 text-xs text-center font-mono py-1.5 px-3 rounded-xs border border-yellow-400 bg-yellow-100 shadow-sm" style={{ color: INK }}>
            {statusBanner}
          </div>
        )}

        <main className="flex-1 overflow-y-auto px-4 py-4">

          {/* MAIN HERO: Giant Yellow Post-it Note */}
          <div
            className="p-5 rounded-xs relative transition-transform duration-200 hover:rotate-0"
            style={{
              background: POSTIT_YELLOW,
              boxShadow: STICKY_SHADOW,
              transform: 'rotate(-0.8deg)',
            }}
          >
            {/* Top Tape Strip */}
            <div className="h-3 absolute -top-1.5 left-1/3 right-1/3 bg-amber-400/30 rounded-xs shadow-2xs backdrop-blur-xs" />

            <div className="flex items-center justify-between">
              <h2 className="font-serif text-xl font-bold flex items-center gap-1.5" style={{ color: INK }}>
                {fullName}
                <span className="w-2 h-2 rounded-full bg-amber-500 shadow-xs" title="verified stickie" />
              </h2>
              <span className="text-[10px] font-mono uppercase bg-amber-200/60 px-2 py-0.5 rounded-xs border border-amber-300">
                {cadence} Sync
              </span>
            </div>

            {/* Spontaneous Status Buttons */}
            <div className="mt-4 pt-3 border-t border-yellow-300/70 flex items-center justify-between">
              <span style={{ ...labeled, color: '#854D0E' }}>Spontaneous Mode</span>
              <div className="flex gap-1.5">
                {['Active', 'Busy', 'Off'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setPresence(mode)}
                    className="px-2.5 py-1 text-[10px] font-mono rounded-xs border transition shadow-2xs"
                    style={
                      presence === mode
                        ? { background: '#FACC15', color: INK, borderColor: '#CA8A04', fontWeight: 700 }
                        : { background: '#FFFBEB', color: MUTED, borderColor: '#FDE68A' }
                    }
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            {/* Interests Teaser */}
            <button
              onClick={() => setView('settings')}
              className="w-full mt-3 pt-2 border-t border-yellow-300/60 flex items-center justify-between text-left group"
            >
              <span style={{ ...labeled, color: '#854D0E' }}>Interests</span>
              <span className="flex items-center gap-1 text-[11px] font-mono font-medium text-amber-900 group-hover:underline">
                {selectedInterests.slice(0, 2).join(', ')}
                {selectedInterests.length > 2 ? ` +${selectedInterests.length - 2}` : ''}
                <span className="text-amber-600 font-bold ml-1">→</span>
              </span>
            </button>
          </div>

          {/* TAB TAPE SELECTOR */}
          <div className="flex gap-2 mt-6 mb-4 px-1">
            {[
              { id: 'friends', label: 'Crew Notes', color: POSTIT_BLUE },
              { id: 'hangouts', label: 'Past Moments', color: POSTIT_PINK }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="flex-1 py-2 text-xs font-mono uppercase tracking-wider rounded-xs border transition shadow-2xs text-center"
                style={{
                  background: activeTab === tab.id ? tab.color : '#F5EFE1',
                  borderColor: activeTab === tab.id ? '#94A3B8' : '#E2D8C0',
                  fontWeight: activeTab === tab.id ? 700 : 500,
                  transform: activeTab === tab.id ? 'translateY(-1px)' : 'none',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: CREW NOTES (SQUARE POST-IT 2-COLUMN GRID) */}
          {activeTab === 'friends' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <span style={labeled}>Sticky Roll Call</span>
                <button
                  onClick={() => setShowAddFriend(!showAddFriend)}
                  className="text-[11px] font-mono hover:underline font-semibold text-amber-900"
                >
                  {showAddFriend ? 'close' : '+ Pin New Friend'}
                </button>
              </div>

              {showAddFriend && (
                <form
                  onSubmit={handleAddFriend}
                  className="p-3.5 rounded-xs space-y-2 shadow-md relative"
                  style={{ background: POSTIT_YELLOW, border: '1px solid #FCD34D' }}
                >
                  <div className="h-1.5 absolute top-0 left-0 right-0 bg-yellow-400/30" />
                  <div className="text-[11px] font-mono font-bold text-amber-900">Pin contact:</div>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text" placeholder="Name" value={newFriendName}
                      onChange={(e) => setNewFriendName(e.target.value)}
                      className="px-2 py-1 text-xs border border-amber-300 rounded-xs outline-none bg-white/90"
                    />
                    <input
                      type="tel" placeholder="Phone" value={newFriendPhone}
                      onChange={(e) => setNewFriendPhone(e.target.value)}
                      className="px-2 py-1 text-xs border border-amber-300 rounded-xs outline-none bg-white/90"
                    />
                  </div>
                  <button type="submit" className="w-full py-1 rounded-xs text-xs font-bold bg-amber-400 text-stone-900 hover:bg-amber-300 shadow-2xs">
                    Pin to Board
                  </button>
                </form>
              )}

              {crewLoading && crew.mutual.length === 0 && crew.solo.length === 0 && (
                <p className="text-xs font-mono text-center py-6 text-stone-400">Loading sticky pins...</p>
              )}

              {/* 2-Column Square Grid for Crew Notes */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                {/* MUTUAL STICKIES (Square Blue/Yellow Notes) */}
                {crew.mutual.map((friend, idx) => (
                  <div
                    key={friend.other_phone}
                    className="aspect-square p-3 rounded-xs flex flex-col justify-between relative transition duration-150 hover:rotate-0 hover:scale-[1.02]"
                    style={{
                      background: friend.overdue ? '#FEF08A' : POSTIT_BLUE,
                      border: friend.overdue ? '1px solid #FACC15' : '1px solid #BAE6FD',
                      boxShadow: STICKY_SHADOW,
                      transform: idx % 2 === 0 ? 'rotate(-0.8deg)' : 'rotate(0.9deg)',
                    }}
                  >
                    {/* Adhesive tape bar */}
                    <div className="h-1.5 absolute top-0 left-0 right-0 rounded-t-xs bg-black/5" />

                    {/* Top Row: Avatar & Status */}
                    <div className="flex items-start justify-between">
                      <div
                        className="w-8 h-8 rounded-xs flex items-center justify-center font-mono text-xs font-bold shadow-2xs bg-white"
                        style={{ border: '1px solid rgba(0,0,0,0.1)', color: INK }}
                      >
                        {friend.other_name.slice(0, 2).toUpperCase()}
                      </div>
                      {friend.overdue && (
                        <span className="text-[8px] font-mono uppercase px-1 py-0.5 rounded-xs bg-amber-400 text-amber-950 font-bold">
                          overdue
                        </span>
                      )}
                    </div>

                    {/* Middle Info */}
                    <div className="my-auto py-1">
                      <div className="text-xs font-bold truncate leading-tight" style={{ color: INK }}>
                        {friend.other_name}
                      </div>
                      <span className="text-[8px] font-mono uppercase tracking-wider text-sky-900 block mt-0.5">
                        stickie user
                      </span>
                      <div className="text-[9px] font-mono mt-1 leading-tight" style={{ color: MUTED }}>
                        {friend.days_since === null ? 'no hangouts yet' : `${friend.days_since}d ago`}
                      </div>
                    </div>

                    {/* Bottom Action */}
                    <button
                      onClick={() => nudgeOne('mutual', friend.other_phone)}
                      className="w-full text-[10px] font-mono py-1 rounded-xs border font-bold bg-white text-stone-800 border-stone-300 shadow-xs active:translate-y-0.5 hover:bg-stone-50"
                    >
                      nudge ⚡️
                    </button>
                  </div>
                ))}

                {/* SOLO STICKIES (Square Yellow Notes) */}
                {crew.solo.map((contact, idx) => (
                  <div
                    key={contact.key}
                    className="aspect-square p-3 rounded-xs flex flex-col justify-between relative transition duration-150 hover:rotate-0 hover:scale-[1.02]"
                    style={{
                      background: contact.overdue ? '#FED7AA' : POSTIT_YELLOW,
                      border: contact.overdue ? '1px solid #FB923C' : '1px solid #FDE047',
                      boxShadow: STICKY_SHADOW,
                      transform: idx % 2 === 0 ? 'rotate(0.8deg)' : 'rotate(-0.7deg)',
                    }}
                  >
                    {/* Adhesive tape bar */}
                    <div className="h-1.5 absolute top-0 left-0 right-0 rounded-t-xs bg-amber-400/20" />

                    {/* Top Row: Avatar & Status */}
                    <div className="flex items-start justify-between">
                      <div
                        className="w-8 h-8 rounded-xs flex items-center justify-center font-mono text-xs font-bold shadow-2xs bg-white/90 border border-amber-300"
                        style={{ color: INK }}
                      >
                        {contact.other_name.slice(0, 2).toUpperCase()}
                      </div>
                      {contact.overdue && (
                        <span className="text-[8px] font-mono uppercase px-1 py-0.5 rounded-xs bg-orange-400 text-white font-bold">
                          overdue
                        </span>
                      )}
                    </div>

                    {/* Middle Info */}
                    <div className="my-auto py-1">
                      <div className="text-xs font-bold truncate leading-tight" style={{ color: INK }}>
                        {contact.other_name}
                      </div>
                      <div className="text-[9px] font-mono mt-0.5" style={{ color: MUTED }}>
                        {contact.days_since === null ? 'not met yet' : `met ${contact.days_since}d ago`}
                      </div>
                      <select
                        value={DAYS_TO_CADENCE[contact.cadence_days] || 'Monthly'}
                        onChange={(e) => updateContactCadence(contact.key, e.target.value)}
                        className="text-[9px] font-mono bg-transparent border-b border-amber-500/40 outline-none font-bold text-amber-900 mt-1 cursor-pointer"
                      >
                        <option value="Weekly">weekly</option>
                        <option value="Bi-weekly">bi-weekly</option>
                        <option value="Monthly">monthly</option>
                      </select>
                    </div>

                    {/* Bottom Action */}
                    <button
                      onClick={() => nudgeOne('solo', contact.key)}
                      className="w-full text-[10px] font-mono py-1 rounded-xs border font-bold bg-white text-amber-900 border-amber-300 shadow-xs active:translate-y-0.5 hover:bg-amber-50"
                    >
                      nudge ⚡️
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: PAST MOMENTS (HORIZONTAL RECTANGLES WITH BOTTOM-RIGHT DOG EAR) */}
          {activeTab === 'hangouts' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between px-1">
                <span style={labeled}>Scrapbook Timeline</span>
                <span className="text-[10px] font-mono text-stone-500">{PAST_HANGOUTS.length} sticky memories</span>
              </div>

              {groupByMonth(PAST_HANGOUTS).map((group) => (
                <div key={group.month}>
                  <div className="inline-block px-2 py-0.5 text-[11px] font-mono font-bold tracking-wider rounded-xs bg-stone-200 border border-stone-300 text-stone-700 mb-3 shadow-2xs">
                    {group.month.toUpperCase()} LOG
                  </div>
                  <div className="space-y-3.5 pl-1">
                    {group.events.map((event, i) => (
                      <div
                        key={event.id}
                        className="p-3.5 rounded-xs relative transition duration-150 hover:rotate-0 flex gap-3 justify-between overflow-hidden"
                        style={{
                          background: i % 2 === 0 ? POSTIT_YELLOW : POSTIT_GREEN,
                          border: i % 2 === 0 ? '1px solid #FDE047' : '1px solid #A7F3D0',
                          boxShadow: STICKY_SHADOW,
                          transform: i % 2 === 0 ? 'rotate(-0.7deg)' : 'rotate(0.6deg)',
                        }}
                      >
                        {/* Adhesive top strip */}
                        <div className="h-2 absolute top-0 left-0 right-0 rounded-t-xs bg-black/5" />

                        {/* Bottom-right Dog-Ear Fold */}
                        <div
                          className="absolute bottom-0 right-0 pointer-events-none"
                          style={{
                            width: 0,
                            height: 0,
                            borderStyle: 'solid',
                            borderWidth: '0 0 16px 16px',
                            borderColor: `transparent transparent ${DESK_BG} transparent`,
                          }}
                        />
                        <div
                          className="absolute bottom-0 right-0 pointer-events-none"
                          style={{
                            width: 0,
                            height: 0,
                            borderStyle: 'solid',
                            borderWidth: '16px 16px 0 0',
                            borderColor: `rgba(0, 0, 0, 0.12) transparent transparent transparent`,
                          }}
                        />

                        <div className="min-w-0 flex-1 pr-3">
                          <div className="text-[9px] font-mono font-bold text-amber-900/70">{event.date}</div>
                          <h4 className="font-serif text-sm font-bold mt-0.5 text-stone-900">{event.title}</h4>
                          <p className="text-[10px] font-mono text-stone-600 mt-0.5">📍 {event.venue}</p>
                          <p className="text-[11px] italic mt-1.5 leading-snug text-stone-700 bg-white/50 p-1.5 rounded-xs border border-black/5">
                            "{event.note}"
                          </p>
                        </div>
                        <div className="text-[9px] font-mono text-right shrink-0 pl-2.5 border-l border-black/10 flex flex-col justify-center text-stone-600 pr-1">
                          {event.attendees.split(', ').map((n) => (
                            <div key={n} className="font-medium">{n}</div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

        </main>

        <footer className="sticky bottom-0 z-40 backdrop-blur-md border-t border-[#e2d5b6] py-3 flex items-center justify-center bg-[#fbf8f1]/90">
          <span className="text-[11px] font-mono tracking-wider text-stone-400">
            stickie • plans pinned &amp; sealed
          </span>
        </footer>

      </div>
    </div>
  );
}