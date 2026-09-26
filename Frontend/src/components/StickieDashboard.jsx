import React, { useState } from 'react';
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

const INITIAL_FRIENDS = [
  { id: 1, name: "Anvi", handle: "@anvi_m", status: "Active", cadence: "Weekly", lastMet: "3d ago", tag: "AN" },
  { id: 2, name: "Bhaumi", handle: "@bhaumi.p", status: "Active", cadence: "Bi-weekly", lastMet: "1w ago", tag: "BP" },
  { id: 3, name: "Ellie", handle: "@ellie_v", status: "In Flow", cadence: "Weekly", lastMet: "Yesterday", tag: "EV" },
  { id: 4, name: "Nancy (Rolodex)", handle: "@nancy_hackgt", status: "Due", cadence: "Monthly", lastMet: "4w ago", tag: "NR" }
];

const PAST_HANGOUTS = [
  {
    id: 101,
    title: "Midtown Trivia Run",
    date: "Sept 24",
    attendees: "Anvi, Bhaumi",
    venue: "Midtown Moon",
    note: "Won 2nd place! Next round is Tuesday.",
    color: "bg-[#eaf3fc] border-[#cfe2f8] shadow-[3px_4px_1px_rgba(186,211,238,0.7)] rotate-[-1.5deg]"
  },
  {
    id: 102,
    title: "Westside Pickleball",
    date: "Sept 18",
    attendees: "Ellie, Bhaumi",
    venue: "Westside Courts",
    note: "3 sets played under the lights.",
    color: "bg-[#f2effb] border-[#dfd7f7] shadow-[3px_4px_1px_rgba(209,198,245,0.7)] rotate-[1.2deg]"
  },
  {
    id: 103,
    title: "Spontaneous Coffee Spark",
    date: "Sept 12",
    attendees: "Bhaumi",
    venue: "Student Center Lounge",
    note: "15-min iced matcha break between classes.",
    color: "bg-[#fdfaf2] border-[#faecc7] shadow-[3px_4px_1px_rgba(245,232,188,0.8)] rotate-[-0.8deg]"
  },
  {
    id: 104,
    title: "Late Night Boba Run",
    date: "Sept 04",
    attendees: "Sophie, Anvi",
    venue: "Sweet Hut Bakery",
    note: "Crossover catchup session!",
    color: "bg-[#f0f7f4] border-[#d4ede2] shadow-[3px_4px_1px_rgba(195,228,214,0.7)] rotate-[1.8deg]"
  }
];

export default function StickieDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authEmail, setAuthEmail] = useState('sophie@stickie.app');
  const [authPassword, setAuthPassword] = useState('••••••••');

  const [username, setUsername] = useState('sophiekeller');
  const [fullName, setFullName] = useState('Sophie Keller');
  const [pronouns, setPronouns] = useState('she/her');
  const [phone, setPhone] = useState('+14041234567');
  const [email, setEmail] = useState('sophie@stickie.app');
  const [bio, setBio] = useState('making plans stick.\nOxford → UGA.\nalways down for trivia, iced matcha, or court time.');
  const [cadence, setCadence] = useState('Weekly');
  const [presence, setPresence] = useState('Active');

  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('interests');
  const [statusBanner, setStatusBanner] = useState('');

  const [selectedInterests, setSelectedInterests] = useState(['Trivia Nights', 'Coffee Catchups', 'Pickleball']);
  const [customTagInput, setCustomTagInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const [friendsList, setFriendsList] = useState(INITIAL_FRIENDS);
  const [newFriendName, setNewFriendName] = useState('');
  const [newFriendPhone, setNewFriendPhone] = useState('');
  const [showAddFriend, setShowAddFriend] = useState(false);

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

  const handleAddFriend = (e) => {
    e.preventDefault();
    if (!newFriendName.trim() || !newFriendPhone.trim()) return;
    setFriendsList(prev => [
      ...prev,
      {
        id: Date.now(),
        name: newFriendName.trim(),
        handle: `@${newFriendName.toLowerCase().replace(/\s+/g, '')}`,
        cadence: 'Monthly',
        lastMet: 'Just added',
        status: 'Active',
        tag: newFriendName.slice(0, 2).toUpperCase()
      }
    ]);
    setNewFriendName('');
    setNewFriendPhone('');
    setShowAddFriend(false);
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

  // ==========================================
  // VIEW 1: AUTH / LOGIN NOTE
  // ==========================================
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#edf3fa] text-slate-800 flex flex-col justify-center items-center p-6 font-sans">
        <div className="w-full max-w-sm bg-[#fafcfe] border border-blue-200/80 rounded-2xl p-8 shadow-[4px_6px_0px_0px_rgba(186,211,238,0.7)] relative rotate-[-0.5deg]">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-20 h-6 bg-blue-100/80 border border-blue-200/60 rounded-xs backdrop-blur-xs opacity-90 shadow-xs" />

          <div className="flex flex-col items-center mb-6 pt-2">
            <div className="w-12 h-12 rounded-xl bg-blue-100/70 border border-blue-200 flex items-center justify-center font-mono font-bold text-blue-900 mb-3 shadow-inner">
              [S]
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Stickie</h1>
            <p className="text-xs text-blue-900/60 mt-0.5">plans that stick.</p>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); setIsLoggedIn(true); }} className="space-y-3.5">
            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">
                handle / email
              </label>
              <input
                type="text"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full px-3.5 py-2 text-xs bg-white border border-blue-200 rounded-lg text-slate-800 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition"
                required
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">
                passcode
              </label>
              <input
                type="password"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                className="w-full px-3.5 py-2 text-xs bg-white border border-blue-200 rounded-lg text-slate-800 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition"
                required
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 mt-2 rounded-lg text-xs font-semibold bg-blue-800 hover:bg-blue-900 text-white shadow-xs transition active:scale-[0.98] cursor-pointer"
            >
              open notepad
            </button>
          </form>

          <div className="mt-6 text-center text-[11px] font-mono text-slate-400">
            expo quick-access enabled
          </div>
        </div>
      </div>
    );
  }

  // ==========================================
  // VIEW 2: PROFILE & NOTEBOARD
  // ==========================================
  return (
    <div className="min-h-screen bg-[#edf3fa] text-slate-800 flex flex-col items-center font-sans">
      <div className="w-full max-w-md min-h-screen flex flex-col justify-between bg-[#f8fbfe] border-x border-blue-200/60 shadow-[0_0_25px_rgba(186,211,238,0.35)] relative">

        {/* TOP BAR */}
        <header className="sticky top-0 z-40 bg-[#f8fbfe]/95 backdrop-blur-md px-5 py-3.5 flex items-center justify-between border-b border-blue-100">
          <div className="w-7 h-7 rounded-md bg-blue-100/70 border border-blue-200/80 flex items-center justify-center font-mono text-[11px] font-bold text-blue-900 shadow-xs">
            [S]
          </div>

          <div className="flex items-center gap-1 font-mono text-xs font-bold text-slate-800">
            <span>@{username}</span>
            <span className="text-[10px] text-blue-400">▾</span>
          </div>

          <button
            onClick={() => setMenuOpen(true)}
            className="w-7 h-7 flex flex-col justify-center items-end gap-1 px-0.5 text-slate-600 hover:text-slate-900 cursor-pointer"
            aria-label="Settings"
          >
            <span className="w-4 h-[1.5px] bg-slate-700 rounded-full" />
            <span className="w-3.5 h-[1.5px] bg-slate-700 rounded-full" />
            <span className="w-2.5 h-[1.5px] bg-slate-700 rounded-full" />
          </button>
        </header>

        {statusBanner && (
          <div className="mx-4 mt-2 text-xs text-center font-mono bg-blue-100/80 border border-blue-200 text-blue-950 py-1.5 px-3 rounded-lg">
            {statusBanner}
          </div>
        )}

        <main className="flex-1 overflow-y-auto">

          {/* PROFILE CARD */}
          <div className="flex flex-col items-center pt-6 pb-4 px-6">
            <div className="relative">
              <div className="w-22 h-22 rounded-full bg-blue-50 border-2 border-dashed border-blue-300 p-1 shadow-xs">
                <div className="w-full h-full rounded-full bg-blue-100/60 flex items-center justify-center font-mono font-bold text-lg text-blue-900">
                  SK
                </div>
              </div>
              <div className="absolute bottom-0 right-0 w-6 h-6 rounded-full bg-blue-700 border-2 border-white flex items-center justify-center text-[10px] text-white font-mono font-bold">
                +
              </div>
            </div>

            <h2 className="text-base font-bold text-slate-900 mt-3 flex items-center gap-1.5">
              {fullName}
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600" title="verified" />
            </h2>

            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[11px] font-mono text-blue-900/70 bg-blue-100/60 px-2 py-0.5 rounded border border-blue-200/50">
                {pronouns}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-[11px] text-slate-500 font-mono">{cadence.toLowerCase()} review</span>
            </div>

            {/* 3-STAT TIKTOK RIBBON */}
            <div className="flex items-center justify-center gap-7 my-4 w-full border-y border-blue-100/80 py-3">
              <div className="flex flex-col items-center">
                <span className="text-sm font-bold font-mono text-slate-900">12</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Hangouts</span>
              </div>
              <div className="h-5 w-[1px] bg-blue-200/70" />
              <div className="flex flex-col items-center">
                <span className="text-sm font-bold font-mono text-slate-900">{friendsList.length}</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Rolodex</span>
              </div>
              <div className="h-5 w-[1px] bg-blue-200/70" />
              <div className="flex flex-col items-center">
                <span className="text-sm font-bold font-mono text-slate-900">94%</span>
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Stick Rate</span>
              </div>
            </div>

            {/* BIO */}
            <div className="w-full text-left bg-[#f2f7fd] border border-blue-100 rounded-xl p-3 shadow-xs">
              <p className="text-xs text-slate-700 whitespace-pre-line leading-relaxed font-sans">
                {bio}
              </p>
              <div className="text-[11px] font-mono text-blue-700 mt-2 hover:underline cursor-pointer">
                stickie.app/@{username}
              </div>
            </div>
          </div>

          {/* TABS (UNDERLINE NAV) */}
          <div className="sticky top-[52px] z-30 bg-[#f8fbfe] border-b border-blue-200/70 flex">
            {[
              { id: 'interests', label: 'Interests' },
              { id: 'friends', label: 'Rolodex' },
              { id: 'hangouts', label: 'History' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2.5 text-xs font-mono uppercase tracking-wider relative transition ${
                  activeTab === tab.id ? 'text-blue-950 font-bold' : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-6 right-6 h-[2px] bg-blue-800 rounded-full" />
                )}
              </button>
            ))}
          </div>

          {/* TAB PANELS */}
          <div className="p-5 min-h-[340px]">
            
            {/* TAB 1: INTERESTS */}
            {activeTab === 'interests' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                    taste index
                  </span>
                  <span className="text-[11px] font-mono text-blue-900">
                    {selectedInterests.length} tagged
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  {DEFAULT_INTERESTS.map((tag) => {
                    const isSelected = selectedInterests.includes(tag);
                    return (
                      <button
                        key={tag}
                        onClick={() => toggleInterest(tag)}
                        className={`text-xs px-3 py-1 rounded-md font-sans transition ${
                          isSelected
                            ? 'bg-blue-100/90 text-blue-950 border border-blue-300/80 shadow-[1px_1px_0px_0px_rgba(186,211,238,0.8)] font-medium'
                            : 'bg-white text-slate-600 border border-dashed border-slate-300 hover:border-blue-300'
                        }`}
                      >
                        {isSelected ? '✓ ' : '+ '}
                        {tag}
                      </button>
                    );
                  })}

                  {selectedInterests
                    .filter((t) => !DEFAULT_INTERESTS.includes(t))
                    .map((tag) => (
                      <button
                        key={tag}
                        onClick={() => toggleInterest(tag)}
                        className="text-xs px-3 py-1 rounded-md bg-blue-200/70 border border-blue-300 text-blue-950 font-medium"
                      >
                        ✓ {tag}
                      </button>
                    ))}

                  {!showCustomInput ? (
                    <button
                      type="button"
                      onClick={() => setShowCustomInput(true)}
                      className="text-xs px-3 py-1 rounded-md border border-dotted border-blue-400 text-blue-800 hover:bg-blue-50 transition"
                    >
                      + custom tag
                    </button>
                  ) : (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        autoFocus
                        placeholder="new interest"
                        value={customTagInput}
                        onChange={(e) => setCustomTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleAddCustomInterest(e);
                          if (e.key === 'Escape') setShowCustomInput(false);
                        }}
                        className="px-2 py-0.5 text-xs bg-white border border-blue-300 rounded outline-none"
                      />
                      <button
                        type="button"
                        onClick={handleAddCustomInterest}
                        className="text-xs bg-blue-800 text-white px-2 py-0.5 rounded"
                      >
                        add
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: FRIENDS & ROLODEX */}
            {activeTab === 'friends' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                    squad cadence
                  </span>
                  <button
                    onClick={() => setShowAddFriend(!showAddFriend)}
                    className="text-[11px] font-mono text-blue-800 hover:underline"
                  >
                    {showAddFriend ? 'close' : '+ add contact'}
                  </button>
                </div>

                {showAddFriend && (
                  <form onSubmit={handleAddFriend} className="p-3 bg-white border border-blue-200 rounded-xl space-y-2 mb-3 shadow-xs">
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="Name"
                        value={newFriendName}
                        onChange={(e) => setNewFriendName(e.target.value)}
                        className="px-2.5 py-1 text-xs border border-blue-200 rounded outline-none"
                      />
                      <input
                        type="tel"
                        placeholder="Phone"
                        value={newFriendPhone}
                        onChange={(e) => setNewFriendPhone(e.target.value)}
                        className="px-2.5 py-1 text-xs border border-blue-200 rounded outline-none"
                      />
                    </div>
                    <button
                      type="submit"
                      className="w-full py-1 bg-blue-800 text-white rounded text-xs font-medium"
                    >
                      save to index
                    </button>
                  </form>
                )}

                <div className="space-y-2">
                  {friendsList.map((friend) => (
                    <div
                      key={friend.id}
                      className="p-2.5 bg-white border border-blue-100 rounded-xl flex items-center justify-between shadow-[1px_2px_0px_0px_rgba(219,231,246,0.5)]"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/80 flex items-center justify-center font-mono text-xs font-bold text-blue-900">
                          {friend.tag}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-slate-800">
                            {friend.name}
                            <span className="text-[10px] font-normal text-slate-400 ml-1.5">{friend.handle}</span>
                          </div>
                          <div className="text-[10px] font-mono text-slate-500">
                            seen: {friend.lastMet} • {friend.cadence}
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => setStatusBanner(`Concierge nudge dispatched for ${friend.name}`)}
                        className="text-[10px] font-mono px-2.5 py-1 rounded border border-blue-300 text-blue-900 hover:bg-blue-50"
                      >
                        nudge
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: PAST HANGOUTS (PHYSICAL STICKY NOTE BOARD) */}
            {activeTab === 'hangouts' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                    pinned memories
                  </span>
                  <span className="text-[10px] font-mono text-blue-900">
                    {PAST_HANGOUTS.length} notes
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-1">
                  {PAST_HANGOUTS.map((event) => (
                    <div
                      key={event.id}
                      className={`relative p-3.5 border rounded-lg flex flex-col justify-between min-h-[145px] transition-transform hover:scale-[1.02] cursor-default ${event.color}`}
                    >
                      {/* Translucent Washi Tape Strip at top */}
                      <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-12 h-3.5 bg-white/70 border border-slate-300/40 rounded-xs shadow-2xs backdrop-blur-2xs" />

                      {/* Header */}
                      <div className="flex justify-between items-start pt-1">
                        <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">
                          {event.date}
                        </span>
                        <span className="text-[8px] font-mono text-blue-900 bg-white/80 px-1 py-0.5 rounded border border-slate-200/60">
                          done
                        </span>
                      </div>

                      {/* Body */}
                      <div className="my-1.5">
                        <h4 className="text-xs font-bold text-slate-900 leading-tight">
                          {event.title}
                        </h4>
                        <p className="text-[10px] text-slate-600 font-mono mt-0.5">
                          @{event.venue}
                        </p>
                        <p className="text-[10px] text-slate-500 italic mt-1 leading-snug">
                          "{event.note}"
                        </p>
                      </div>

                      {/* Footer */}
                      <div className="text-[9px] font-mono text-slate-400 border-t border-slate-300/30 pt-1">
                        {event.attendees}
                      </div>
                    </div>
                  ))}

                  {/* Wrapped Post-it Note */}
                  <div className="relative p-3.5 border border-dashed border-blue-300 rounded-lg flex flex-col justify-center items-center text-center min-h-[145px] bg-white/60 shadow-[2px_3px_0px_0px_rgba(203,222,244,0.5)] rotate-[-1deg]">
                    <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-10 h-3 bg-blue-100/80 border border-blue-200/50 rounded-xs" />
                    <span className="text-xs font-mono font-bold text-blue-950 uppercase">
                      Friend Wrapped
                    </span>
                    <span className="text-[10px] text-slate-500 mt-1 font-mono">
                      recap note ready
                    </span>
                  </div>
                </div>
              </div>
            )}

          </div>
        </main>

        {/* MINIMAL FOOTER */}
        <footer className="sticky bottom-0 z-40 bg-[#f8fbfe]/95 backdrop-blur-md border-t border-blue-100 py-3 flex items-center justify-center">
          <span className="text-[11px] font-mono text-slate-400 tracking-wider">
            stickie • plans made simple
          </span>
        </footer>

      </div>

      {/* DRAWER / SETTINGS */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            onClick={() => setMenuOpen(false)}
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-2xs"
          />

          <div className="relative w-full max-w-xs bg-[#fafcfe] border-l border-blue-200 p-6 flex flex-col justify-between overflow-y-auto h-full shadow-xl z-10">
            <div className="space-y-5">
              <div className="flex items-center justify-between border-b border-blue-100 pb-3">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-800">
                  Settings & Index
                </h3>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="text-xs font-mono text-slate-400 hover:text-slate-700"
                >
                  [close]
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-2.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Handle
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full px-2.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                      Pronouns
                    </label>
                    <input
                      type="text"
                      value={pronouns}
                      onChange={(e) => setPronouns(e.target.value)}
                      className="w-full px-2.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                      Review
                    </label>
                    <select
                      value={cadence}
                      onChange={(e) => setCadence(e.target.value)}
                      className="w-full px-1.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                    >
                      <option value="Weekly">Weekly</option>
                      <option value="Bi-weekly">Bi-weekly</option>
                      <option value="Monthly">Monthly</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Sendblue Line
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-2.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Bio Note
                  </label>
                  <textarea
                    rows={3}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    className="w-full px-2.5 py-1 text-xs bg-white border border-blue-200 rounded outline-none"
                  />
                </div>

                {/* Flow C Proximity Spark Trigger */}
                <div className="pt-2 border-t border-blue-100">
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Live Demo Tool
                  </label>
                  <button
                    onClick={triggerProximitySpark}
                    className="w-full py-1.5 bg-blue-800 hover:bg-blue-900 text-white rounded text-xs font-mono font-medium shadow-2xs transition active:scale-[0.98]"
                  >
                    ⚡️ Fire Proximity Spark
                  </button>
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Presence (Flow C)
                  </label>
                  <div className="flex gap-1.5">
                    {['Active', 'Busy', 'Off'].map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setPresence(mode)}
                        className={`flex-1 py-1 text-xs font-mono rounded border transition ${
                          presence === mode
                            ? 'bg-blue-800 text-white border-blue-900'
                            : 'bg-white text-slate-600 border-blue-200'
                        }`}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Manual text commands anyone can send to the Sendblue line */}
                <div className="pt-2 border-t border-blue-100">
                  <label className="block text-[10px] font-mono uppercase text-slate-500 mb-1">
                    Text Commands
                  </label>
                  <div className="space-y-2">
                    <div className="bg-white border border-blue-200 rounded px-2.5 py-1.5">
                      <div className="text-xs font-mono font-bold text-blue-800">/website</div>
                      <div className="text-[10px] text-slate-500">
                        texts you back a link straight into your dashboard, already signed in
                      </div>
                    </div>
                    <div className="bg-white border border-blue-200 rounded px-2.5 py-1.5">
                      <div className="text-xs font-mono font-bold text-blue-800">/plan &lt;activity&gt;</div>
                      <div className="text-[10px] text-slate-500">
                        e.g. "/plan pickleball" — skips the wait-and-detect and starts a real group plan right now
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => { setIsLoggedIn(false); setMenuOpen(false); }}
              className="w-full mt-6 py-2 rounded text-xs font-mono border border-slate-300 text-slate-600 hover:bg-slate-100 transition"
            >
              sign out
            </button>
          </div>
        </div>
      )}

    </div>
  );
}