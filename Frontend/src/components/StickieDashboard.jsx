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

// TODO(real data): still mock -- no backend endpoint returns real
// confirmed-plan history yet. Wire this to real Plan rows before demoing
// this tab as if it were live data. Month groups entries on the timeline
// (shown once per group, not repeated per card).
const PAST_HANGOUTS = [
  { id: 101, month: "Sept", title: "Midtown Trivia Run", date: "Sept 24", attendees: "Anvi, Bhaumi", venue: "Midtown Moon", note: "Won 2nd place! Next round is Tuesday." },
  { id: 102, month: "Sept", title: "Westside Pickleball", date: "Sept 18", attendees: "Ellie, Bhaumi", venue: "Westside Courts", note: "3 sets played under the lights." },
  { id: 103, month: "Sept", title: "Spontaneous Coffee Spark", date: "Sept 12", attendees: "Bhaumi", venue: "Student Center Lounge", note: "15-min iced matcha break between classes." },
  { id: 104, month: "Aug", title: "Late Night Boba Run", date: "Aug 04", attendees: "Sophie, Anvi", venue: "Sweet Hut Bakery", note: "Crossover catchup session!" },
];

// Design tokens shared with Onboarding.jsx -- dark/cream/gold.
const PAGE_BG = '#EDE6D6';
const CARD_BG = '#FFFDF8';
const ACCENT = '#F0C94C';
const INK = '#2b2620';
const MUTED = '#8a7d68';

const CADENCE_DAYS = { Weekly: 7, 'Bi-weekly': 14, Monthly: 30 };
const DAYS_TO_CADENCE = { 7: 'Weekly', 14: 'Bi-weekly', 30: 'Monthly' };

function Logo({ size = 28, cutoutColor = CARD_BG, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-lg relative overflow-hidden shadow-xs shrink-0 ${onClick ? 'cursor-pointer' : ''}`}
      style={{ background: ACCENT, width: size, height: size }}
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

// This dashboard only renders once App.jsx has already verified the
// visitor (real phone + real name saved) -- there is no separate login
// step here, and there never should be one, since that would just be a
// second, fake gate in front of a real one.
export default function StickieDashboard({ name = '', phone: realPhone = '', interests = [], nudgeThresholdDays = null }) {
  const [fullName, setFullName] = useState(name || 'Stickie User');
  const [pronouns, setPronouns] = useState('they/them');
  const [phone, setPhone] = useState(realPhone || '');
  const [cadence, setCadence] = useState(DAYS_TO_CADENCE[nudgeThresholdDays] || 'Monthly');
  const [presence, setPresence] = useState('Active');
  const [hasCalendar, setHasCalendar] = useState(null);

  const [view, setView] = useState('dashboard'); // 'dashboard' | 'settings'
  const [activeTab, setActiveTab] = useState('friends'); // 'friends' | 'hangouts'
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

  const sortOverdueFirst = (list) =>
    [...list].sort((a, b) => (b.overdue ? 1 : 0) - (a.overdue ? 1 : 0));

  const fetchCrew = () => {
    if (!phone) {
      console.warn('⚠️ fetchCrew skipped: phone is empty');
      return;
    }
    setCrewLoading(true);
    fetch(`${API_BASE}/crew?phone=${encodeURIComponent(phone)}`)
      .then(async (r) => {
        if (!r.ok) {
          const errText = await r.text();
          throw new Error(`HTTP ${r.status}: ${errText}`);
        }
        return r.json();
      })
      .then((data) => {
        console.log('✅ Crew data received:', data);
        setCrew({
          mutual: sortOverdueFirst(data.mutual || []),
          solo: sortOverdueFirst(data.solo || []),
          nudge_threshold_days: data.nudge_threshold_days,
        });
      })
      .catch((err) => {
        console.error('❌ fetchCrew failed:', err);
      })
      .finally(() => setCrewLoading(false));
  };

  useEffect(() => {
    if (activeTab === 'friends') fetchCrew();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  useEffect(() => {
    if (!phone) return;
    fetch(`${API_BASE}/users/status?phone=${encodeURIComponent(phone)}`)
      .then((r) => r.json())
      .then((data) => setHasCalendar(Boolean(data.has_calendar)))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    setStatusBanner('Sending...');
    try {
      const res = await fetch(`${API_BASE}/api/nudge-one`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, kind, key }),
      });
      setStatusBanner(res.ok ? 'Nudge sent' : 'Could not send that nudge');
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
    setStatusBanner('Dispatching proximity ping...');
    try {
      const res = await fetch(`${API_BASE}/api/simulate-proximity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_a_name: fullName.split(' ')[0] || 'Sophie',
          user_b_name: 'Bhaumi',
          target_phone: phone,
          location_name: 'Student Center Coffee Lounge'
        })
      });
      if (res.ok) {
        setStatusBanner('Ping delivered to your device.');
        setTimeout(() => setStatusBanner(''), 4500);
      }
    } catch (err) {
      setStatusBanner('Trigger failed: ' + err.message);
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
      // best-effort -- next load will just show the last saved value
    }
  };

  const connectCalendar = () => {
    window.location.href = `${API_BASE}/oauth/google/start?phone=${encodeURIComponent(phone)}`;
  };

  const labeled = { fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'monospace', color: MUTED };

  // ============================================================
  // SETTINGS -- its own full page, not a slide-over drawer.
  // ============================================================
  if (view === 'settings') {
    return (
      <div className="min-h-screen text-[#2b2620] flex flex-col items-center font-sans" style={{ background: PAGE_BG }}>
        <div className="w-full max-w-md min-h-screen flex flex-col border-x border-[#e6dcc2]" style={{ background: CARD_BG }}>
          <header className="px-5 py-4 flex items-center gap-3">
            <Logo size={30} cutoutColor={CARD_BG} onClick={() => setView('dashboard')} />
            <h1 className="font-serif-stickie text-lg font-bold" style={{ color: INK }}>Settings</h1>
          </header>

          <main className="flex-1 overflow-y-auto px-5 pb-10 space-y-8">
            {/* Profile & Account */}
            <section className="space-y-3">
              <div style={{ ...labeled, color: '#8a5a1f', fontWeight: 700 }}>Profile &amp; Account</div>
              <div>
                <label className="block mb-1" style={labeled}>Display Name</label>
                <input
                  type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border rounded-lg outline-none"
                  style={{ borderColor: '#e6dcc2' }}
                />
              </div>
              <div>
                <label className="block mb-1" style={labeled}>Phone Number</label>
                <input
                  type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border rounded-lg outline-none"
                  style={{ borderColor: '#e6dcc2' }}
                />
              </div>
              <div>
                <label className="block mb-1" style={labeled}>Pronouns</label>
                <select
                  value={pronouns} onChange={(e) => setPronouns(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border rounded-lg outline-none"
                  style={{ borderColor: '#e6dcc2' }}
                >
                  <option value="they/them">they/them</option>
                  <option value="she/her">she/her</option>
                  <option value="he/him">he/him</option>
                </select>
              </div>
            </section>

            {/* Preferences & Scheduling */}
            <section className="space-y-3">
              <div style={{ ...labeled, color: '#8a5a1f', fontWeight: 700 }}>Preferences &amp; Scheduling</div>
              <div>
                <label className="block mb-1" style={labeled}>Check-in with crew every</label>
                <select
                  value={cadence} onChange={(e) => updateCadence(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border rounded-lg outline-none"
                  style={{ borderColor: '#e6dcc2' }}
                >
                  <option value="Weekly">1 week</option>
                  <option value="Bi-weekly">2 weeks</option>
                  <option value="Monthly">1 month</option>
                </select>
              </div>
              <div>
                <label className="block mb-1" style={labeled}>Spontaneous availability</label>
                <div className="flex gap-1.5">
                  {['Active', 'Busy', 'Off'].map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setPresence(mode)}
                      className="flex-1 py-1.5 text-xs font-mono rounded-lg border transition"
                      style={
                        presence === mode
                          ? { background: ACCENT, color: INK, borderColor: '#d8b95a', fontWeight: 700 }
                          : { background: '#fff', color: MUTED, borderColor: '#e6dcc2' }
                      }
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Interests -- moved here from its own tab */}
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <div style={{ ...labeled, color: '#8a5a1f', fontWeight: 700 }}>Interests</div>
                <span style={labeled}>{selectedInterests.length} tagged</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {DEFAULT_INTERESTS.map((tag) => {
                  const isSelected = selectedInterests.includes(tag);
                  return (
                    <button
                      key={tag}
                      onClick={() => toggleInterest(tag)}
                      className="text-xs px-3 py-1 rounded-md font-medium transition"
                      style={
                        isSelected
                          ? { background: '#F3E4A8', color: INK, border: '1px solid #EAD68F' }
                          : { background: '#fff', color: MUTED, border: '1px dashed #e0d5b8' }
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
                    className="text-xs px-3 py-1 rounded-md font-medium"
                    style={{ background: ACCENT, color: INK }}
                  >
                    ✓ {tag}
                  </button>
                ))}
                {!showCustomInput ? (
                  <button
                    type="button"
                    onClick={() => setShowCustomInput(true)}
                    className="text-xs px-3 py-1 rounded-md border border-dotted"
                    style={{ borderColor: '#d8b95a', color: INK }}
                  >
                    + custom tag
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
                      className="px-2 py-1 text-xs bg-white border rounded outline-none"
                      style={{ borderColor: '#d8b95a' }}
                    />
                    <button onClick={handleAddCustomInterest} className="text-xs px-2 py-1 rounded font-semibold" style={{ background: ACCENT, color: INK }}>
                      add
                    </button>
                  </div>
                )}
              </div>
            </section>

            {/* Connected Services */}
            <section className="space-y-2">
              <div style={{ ...labeled, color: '#8a5a1f', fontWeight: 700 }}>Connected Services</div>
              <div className="flex items-center justify-between p-3 rounded-lg border" style={{ background: '#FBEEDD', borderColor: '#EAD8B8' }}>
                <div>
                  <div className="text-sm font-bold" style={{ color: INK }}>Google Calendar</div>
                  <div className="text-[11px] font-mono" style={{ color: hasCalendar ? '#4a7a4a' : MUTED }}>
                    {hasCalendar === null ? 'checking...' : hasCalendar ? 'Connected (syncing active)' : 'Not connected'}
                  </div>
                </div>
                <button
                  onClick={connectCalendar}
                  className="text-[11px] font-mono px-3 py-1.5 rounded-lg border font-semibold"
                  style={{ borderColor: '#E2C692', color: '#8a5a1f', background: '#fff' }}
                >
                  {hasCalendar ? 'reconnect' : 'connect'}
                </button>
              </div>
            </section>

            {/* Text Commands */}
            <section className="space-y-2">
              <div style={{ ...labeled, color: '#8a5a1f', fontWeight: 700 }}>Text Commands</div>
              {[
                { cmd: '/website', desc: 'Texts you back a link straight into your dashboard, already signed in.' },
                { cmd: '/plan <activity>', desc: 'Starts a real group plan right now.' },
                { cmd: '/nudge', desc: 'Triggers your overdue crew check-ins — reply with a number to approve before your friend sees anything.' },
              ].map((c) => (
                <div key={c.cmd} className="rounded-lg px-3 py-2 border" style={{ background: '#fff', borderColor: '#e6dcc2' }}>
                  <div className="text-xs font-mono font-bold" style={{ color: '#8a5a1f' }}>{c.cmd}</div>
                  <div className="text-[11px]" style={{ color: MUTED }}>{c.desc}</div>
                </div>
              ))}
            </section>

            {/* Debug tools */}
            <details className="pt-2 border-t" style={{ borderColor: '#efe7d3' }}>
              <summary className="cursor-pointer select-none" style={labeled}>
                Debug tools (hackathon demo only)
              </summary>
              <div className="mt-2">
                <button
                  onClick={triggerProximitySpark}
                  className="w-full py-2 rounded-lg text-xs font-mono font-medium transition active:scale-[0.98]"
                  style={{ background: '#6b6355', color: '#fff' }}
                >
                  Fire Proximity Spark (Flow C demo)
                </button>
              </div>
            </details>

            <button
              onClick={() => { localStorage.removeItem('stickie_phone'); window.location.href = '/'; }}
              className="w-full py-2.5 rounded-xl text-xs font-mono font-semibold border transition"
              style={{ borderColor: '#e0d5b8', color: INK }}
            >
              Sign Out
            </button>
          </main>
        </div>
      </div>
    );
  }

  // ============================================================
  // DASHBOARD
  // ============================================================
  return (
    <div className="min-h-screen text-[#2b2620] flex flex-col items-center font-sans" style={{ background: PAGE_BG }}>
      <div className="w-full max-w-md min-h-screen flex flex-col justify-between border-x border-[#e6dcc2] shadow-[0_0_25px_rgba(0,0,0,0.06)] relative" style={{ background: CARD_BG }}>

        {/* TOP BAR -- logo + settings only, no username/divider */}
        <header className="sticky top-0 z-40 backdrop-blur-md px-5 py-3.5 flex items-center justify-between" style={{ background: CARD_BG + 'f2' }}>
          <Logo size={28} cutoutColor={CARD_BG} />
          <div />
          <button
            onClick={() => setView('settings')}
            className="w-7 h-7 flex flex-col justify-center items-end gap-1 px-0.5 cursor-pointer opacity-70 hover:opacity-100"
            aria-label="Settings"
          >
            <span className="w-4 h-[1.5px] rounded-full" style={{ background: INK }} />
            <span className="w-3.5 h-[1.5px] rounded-full" style={{ background: INK }} />
            <span className="w-2.5 h-[1.5px] rounded-full" style={{ background: INK }} />
          </button>
        </header>

        {statusBanner && (
          <div className="mx-4 mt-2 text-xs text-center font-mono py-1.5 px-3 rounded-lg" style={{ background: '#FBEFC8', border: '1px solid #EAD68F', color: INK }}>
            {statusBanner}
          </div>
        )}

        <main className="flex-1 overflow-y-auto">

          {/* PROFILE CARD -- no photo, no peeking tab: just name, a real
              Spontaneous toggle, and an Interests preview that opens
              Settings to edit. */}
          <div
            className="flex flex-col items-center py-5 px-6 mx-4 mt-4 rounded-2xl border border-[#efe7d3] shadow-[2px_3px_0px_0px_rgba(0,0,0,0.04)]"
            style={{ background: '#FBF6E8' }}
          >
            <h2 className="font-serif-stickie text-lg font-bold flex items-center gap-1.5" style={{ color: INK }}>
              {fullName}
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: ACCENT }} title="verified" />
            </h2>

            <div className="w-full mt-4 flex items-center justify-between">
              <span style={labeled}>Spontaneous</span>
              <div className="flex gap-1">
                {['Active', 'Busy', 'Off'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setPresence(mode)}
                    className="px-2.5 py-1 text-[10px] font-mono rounded-md border transition"
                    style={
                      presence === mode
                        ? { background: ACCENT, color: INK, borderColor: '#d8b95a', fontWeight: 700 }
                        : { background: '#fff', color: MUTED, borderColor: '#e6dcc2' }
                    }
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => setView('settings')}
              className="w-full mt-3 flex items-center justify-between text-left"
            >
              <span style={labeled}>Interests</span>
              <span className="flex items-center gap-1.5 text-[11px] font-mono" style={{ color: '#8a5a1f' }}>
                {selectedInterests.slice(0, 2).join(', ')}
                {selectedInterests.length > 2 ? ` +${selectedInterests.length - 2}` : ''}
                <span style={{ color: ACCENT }}>edit →</span>
              </span>
            </button>
          </div>

          {/* TABS -- Crew / History only */}
          <div className="sticky top-[52px] z-30 border-b flex mt-2" style={{ background: CARD_BG, borderColor: '#efe7d3' }}>
            {[
              { id: 'friends', label: 'Crew' },
              { id: 'hangouts', label: 'History' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="flex-1 py-2.5 text-xs font-mono uppercase tracking-wider relative transition"
                style={{ color: activeTab === tab.id ? INK : '#c2b596', fontWeight: activeTab === tab.id ? 700 : 400 }}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-6 right-6 h-[2px] rounded-full" style={{ background: ACCENT }} />
                )}
              </button>
            ))}
          </div>

          {/* TAB PANELS */}
          <div className="p-5 min-h-[340px]">

            {/* CREW */}
            {activeTab === 'friends' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-1">
                  <span style={labeled}>your crew</span>
                  <button
                    onClick={() => setShowAddFriend(!showAddFriend)}
                    className="text-[11px] font-mono hover:underline font-semibold"
                    style={{ color: INK }}
                  >
                    {showAddFriend ? 'close' : '+ add contact'}
                  </button>
                </div>

                {showAddFriend && (
                  <form onSubmit={handleAddFriend} className="p-3 bg-white border rounded-xl space-y-2 mb-3 shadow-xs" style={{ borderColor: '#e6dcc2' }}>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text" placeholder="Name" value={newFriendName}
                        onChange={(e) => setNewFriendName(e.target.value)}
                        className="px-2.5 py-1 text-xs border rounded outline-none" style={{ borderColor: '#e6dcc2' }}
                      />
                      <input
                        type="tel" placeholder="Phone" value={newFriendPhone}
                        onChange={(e) => setNewFriendPhone(e.target.value)}
                        className="px-2.5 py-1 text-xs border rounded outline-none" style={{ borderColor: '#e6dcc2' }}
                      />
                    </div>
                    <button type="submit" className="w-full py-1 rounded text-xs font-semibold" style={{ background: ACCENT, color: INK }}>
                      save to index
                    </button>
                  </form>
                )}

                <div className="space-y-2">
                  {crewLoading && crew.mutual.length === 0 && crew.solo.length === 0 && (
                    <p className="text-[11px] font-mono text-center py-4" style={{ color: '#c2b596' }}>loading...</p>
                  )}
                  {!crewLoading && crew.mutual.length === 0 && crew.solo.length === 0 && (
                    <p className="text-[11px] font-mono text-center py-4" style={{ color: '#c2b596' }}>no crew yet</p>
                  )}

                  {crew.mutual.map((friend) => (
                    <div
                      key={friend.other_phone}
                      className="p-2.5 border rounded-xl flex items-center justify-between shadow-[1px_2px_0px_0px_rgba(0,0,0,0.03)]"
                      style={friend.overdue ? { background: '#FDF2D9', borderColor: '#EAC97A' } : { background: '#EEF3F6', borderColor: '#D8E3E9' }}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center font-mono text-xs font-bold" style={{ background: '#DCE7ED', border: '1px solid #C6D6DF', color: INK }}>
                          {friend.other_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-xs font-bold flex items-center gap-1.5" style={{ color: INK }}>
                            {friend.other_name}
                            <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded" style={{ background: '#DCE7ED', color: '#4a6472' }}>on stickie</span>
                            {friend.overdue && (
                              <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded" style={{ background: '#EAC97A', color: '#5c4108' }}>overdue</span>
                            )}
                          </div>
                          <div className="text-[10px] font-mono" style={{ color: MUTED }}>
                            {friend.days_since === null ? 'never hung out' : `seen ${friend.days_since}d ago`}
                            {' '}• checked every {crew.nudge_threshold_days || 30}d
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => nudgeOne('mutual', friend.other_phone)}
                        className="text-[10px] font-mono px-2.5 py-1 rounded border font-semibold"
                        style={{ borderColor: '#B8CCD6', color: '#3d5a68', background: '#fff' }}
                      >
                        nudge
                      </button>
                    </div>
                  ))}

                  {crew.solo.map((contact) => (
                    <div
                      key={contact.key}
                      className="p-2.5 border rounded-xl flex items-center justify-between shadow-[1px_2px_0px_0px_rgba(0,0,0,0.03)]"
                      style={contact.overdue ? { background: '#FDF2D9', borderColor: '#EAC97A' } : { background: '#FBEEDD', borderColor: '#EAD8B8' }}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center font-mono text-xs font-bold" style={{ background: '#F3E0BF', border: '1px solid #E2C692', color: INK }}>
                          {contact.other_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-xs font-bold flex items-center gap-1.5" style={{ color: INK }}>
                            {contact.other_name}
                            <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded" style={{ background: '#F3E0BF', color: '#8a5a1f' }}>not on stickie</span>
                            {contact.overdue && (
                              <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded" style={{ background: '#EAC97A', color: '#5c4108' }}>overdue</span>
                            )}
                          </div>
                          <div className="text-[10px] font-mono flex items-center gap-1" style={{ color: MUTED }}>
                            {contact.days_since === null ? 'never met' : `seen ${contact.days_since}d ago`}
                            <select
                              value={DAYS_TO_CADENCE[contact.cadence_days] || 'Monthly'}
                              onChange={(e) => updateContactCadence(contact.key, e.target.value)}
                              className="text-[10px] font-mono bg-transparent border-none outline-none font-semibold"
                              style={{ color: '#8a5a1f' }}
                            >
                              <option value="Weekly">weekly</option>
                              <option value="Bi-weekly">bi-weekly</option>
                              <option value="Monthly">monthly</option>
                            </select>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => nudgeOne('solo', contact.key)}
                        className="text-[10px] font-mono px-2.5 py-1 rounded border font-semibold"
                        style={{ borderColor: '#E2C692', color: '#8a5a1f', background: '#fff' }}
                      >
                        nudge
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* HISTORY -- grouped by month (shown once), attendees on
                the side of each card instead of a bottom footer. */}
            {activeTab === 'hangouts' && (
              <div className="space-y-5">
                <div className="flex items-center justify-between pb-1">
                  <span style={labeled}>timeline</span>
                  <span className="text-[10px] font-mono" style={{ color: INK }}>{PAST_HANGOUTS.length} logged</span>
                </div>

                {groupByMonth(PAST_HANGOUTS).map((group) => (
                  <div key={group.month}>
                    <div className="text-[11px] font-mono uppercase tracking-wider font-bold mb-2" style={{ color: '#8a5a1f' }}>
                      {group.month}
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute left-[7px] top-1 bottom-1 w-[2px]" style={{ background: '#EAD68F' }} />
                      <div className="space-y-3">
                        {group.events.map((event, i) => (
                          <div key={event.id} className="relative">
                            <div
                              className="absolute -left-6 top-1 w-4 h-4 rounded-full border-2 flex items-center justify-center text-[8px] font-mono font-bold"
                              style={{ background: ACCENT, borderColor: CARD_BG, color: INK }}
                            >
                              {i + 1}
                            </div>
                            <div
                              className="rounded-xl p-3 border shadow-[1px_2px_0px_0px_rgba(0,0,0,0.04)] flex gap-3 justify-between"
                              style={{ background: i % 2 === 0 ? '#FBEEDD' : '#EEF3F6', borderColor: i % 2 === 0 ? '#EAD8B8' : '#D8E3E9' }}
                            >
                              <div className="min-w-0 flex-1">
                                <div className="text-[9px] font-mono" style={{ color: MUTED }}>{event.date}</div>
                                <h4 className="font-serif-stickie text-sm font-bold mt-0.5" style={{ color: INK }}>{event.title}</h4>
                                <p className="text-[10px] font-mono mt-0.5" style={{ color: MUTED }}>@{event.venue}</p>
                                <p className="text-[10px] italic mt-1 leading-snug" style={{ color: '#a89877' }}>"{event.note}"</p>
                              </div>
                              <div className="text-[9px] font-mono text-right shrink-0 pl-2 border-l" style={{ color: MUTED, borderColor: '#e6dcc2' }}>
                                {event.attendees.split(', ').map((n) => <div key={n}>{n}</div>)}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

          </div>
        </main>

        <footer className="sticky bottom-0 z-40 backdrop-blur-md border-t py-3 flex items-center justify-center" style={{ background: CARD_BG + 'f2', borderColor: '#efe7d3' }}>
          <span className="text-[11px] font-mono tracking-wider" style={{ color: '#c2b596' }}>
            stickie • plans made simple
          </span>
        </footer>

      </div>
    </div>
  );
}
