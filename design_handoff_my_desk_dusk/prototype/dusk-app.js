// dusk-app.js — vanilla JS app logic (timers, todos, drag, notes, backlog)
// Ported & streamlined from the original index.html. Uses localStorage only
// for this prototype; the real app can layer Firestore on top.

(function() {
  'use strict';

  // ──────── State ────────
  let items = [];
  let backlog = [];
  let themeTick = null;

  const STORAGE_KEY = 'desk-dusk-items';
  const BACKLOG_KEY = 'desk-dusk-backlog';

  // Seed demo data on first run
  function seedIfEmpty() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) { try { items = JSON.parse(stored); return; } catch {} }
    items = [
      { type: 'timer', label: 'Grading admin', totalSeconds: 3600, elapsed: 3600, running: false, notes: '' },
      { type: 'timer', label: 'Reading finals', totalSeconds: 3600, elapsed: 1980, running: false, notes: '' },
      { type: 'timer', label: 'Email', totalSeconds: 1800, elapsed: 0, running: false, notes: '' },
      { type: 'todo',  label: 'Reply to Marcus re: syllabus', checked: false, notes: '' },
      { type: 'timer', label: 'MIT: Image paper', totalSeconds: 1800, elapsed: 420, running: false, notes: '' },
      { type: 'todo',  label: 'Weekend planning', checked: false, notes: 'fri evening — book travel\nsat morning — long walk' },
      { type: 'timer', label: 'Messaging', totalSeconds: 1800, elapsed: 0, running: false, notes: '' },
    ];
    save();
  }
  function seedBacklogIfEmpty() {
    const stored = localStorage.getItem(BACKLOG_KEY);
    if (stored) { try { backlog = JSON.parse(stored); return; } catch {} }
    backlog = [
      { title: 'Draft intro for vision paper', due: 'Today', done: false, overdue: false },
      { title: "Review Jana's revisions", due: 'Tomorrow', done: false, overdue: false },
      { title: 'Book flights for May conference', due: 'Thu', done: false, overdue: false },
      { title: 'Submit expense report', due: 'Apr 18', done: false, overdue: true },
      { title: 'Sketch outline for seminar talk', done: false },
      { title: 'Pick up dry cleaning', done: true },
    ];
    saveBacklog();
  }

  function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(items.map(cleanItem))); }
  function saveBacklog() { localStorage.setItem(BACKLOG_KEY, JSON.stringify(backlog)); }
  function cleanItem(i) {
    const c = {};
    for (const [k, v] of Object.entries(i)) if (!k.startsWith('_') && v !== undefined) c[k] = v;
    return c;
  }

  // ──────── Helpers ────────
  function fmtTime(sec) {
    sec = Math.max(0, Math.round(sec));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }
  function parseTime(str) {
    const parts = str.split(':').map(Number);
    if (parts.some(isNaN)) return null;
    if (parts.length === 3) return parts[0]*3600 + parts[1]*60 + parts[2];
    if (parts.length === 2) return parts[0]*60 + parts[1];
    if (parts.length === 1) return parts[0]*60;
    return null;
  }
  function esc(s) { return (s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  // ──────── Clock ────────
  function tickClock() {
    const now = new Date();
    document.getElementById('clock').textContent = now.toLocaleTimeString('en-US', { hour12: true, hour: 'numeric', minute: '2-digit' });
    document.getElementById('date').textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    // Phase
    const hour = window.__DUSK && window.__DUSK.phaseOverride != null ? window.__DUSK.phaseOverride : now.getHours();
    const phase = window.duskPhaseForHour(hour);
    document.getElementById('phase').textContent = '· ' + window.duskPhaseLabel(phase);
    // Weather glyph by phase
    const glyphs = { dawn: '◐', day: '☀', dusk: '◑', night: '☾' };
    document.getElementById('weather-glyph').textContent = glyphs[phase];
  }

  // ──────── Timer engine ────────
  function startInterval(item) {
    if (item._interval) return;
    item._lastTick = Date.now();
    item._interval = setInterval(() => {
      const now = Date.now();
      item.elapsed += (now - item._lastTick) / 1000;
      item._lastTick = now;
      if (item.elapsed >= item.totalSeconds) {
        item.elapsed = item.totalSeconds;
        item.running = false;
        stopInterval(item);
        save(); renderAll();
        playBell();
        return;
      }
      // Incremental update
      const idx = items.indexOf(item);
      const row = document.getElementById('list').children[idx];
      if (!row) return;
      updateTimerRow(row, item);
    }, 250);
    updateRunningIndicator();
  }
  function stopInterval(item) {
    if (item._interval) { clearInterval(item._interval); item._interval = null; }
    updateRunningIndicator();
  }
  function toggleTimer(item) {
    if (item.elapsed >= item.totalSeconds) return;
    item.running = !item.running;
    if (item.running) startInterval(item); else stopInterval(item);
    save(); renderAll();
  }
  function updateTimerRow(row, item) {
    const pct = item.totalSeconds > 0 ? Math.min(100, (item.elapsed / item.totalSeconds) * 100) : 0;
    const fill = row.querySelector('.bar-fill');
    const head = row.querySelector('.playhead');
    const scrub = row.querySelector('.scrub-handle');
    if (fill) fill.style.width = pct + '%';
    if (head) head.style.left = pct + '%';
    if (scrub) scrub.style.left = pct + '%';
    const disp = row.querySelector('.elapsed-input');
    if (disp && disp !== document.activeElement) disp.value = fmtTime(item.elapsed);
  }
  function updateRunningIndicator() {
    const el = document.getElementById('running-indicator');
    const any = items.some(i => i.type === 'timer' && i.running);
    el.textContent = any ? '● running' : '';
    el.style.color = any ? 'var(--accent)' : 'var(--text-mute)';
  }

  function playBell() {
    if (window.__DUSK && window.__DUSK.muteBell) return;
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const freqs = [523.25, 659.25, 783.99];
      freqs.forEach((f, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine'; osc.frequency.value = f;
        gain.gain.setValueAtTime(0.25, ctx.currentTime + i * 0.15);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.8);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.15);
        osc.stop(ctx.currentTime + i * 0.15 + 0.8);
      });
    } catch {}
  }

  // ──────── Rendering ────────
  const listEl = () => document.getElementById('list');

  function renderTodo(item, idx) {
    const row = document.createElement('div');
    row.className = 'item todo' + (item.checked ? ' checked' : '');
    row.dataset.idx = idx;
    row.setAttribute('draggable', 'true');
    const hasNotes = item.notes && item.notes.trim();
    row.innerHTML = `
      ${item.checked ? '<div class="bar-fill" style="width:100%;background:var(--bar-done)"></div>' : ''}
      <div class="item-content">
        <button class="check-btn ${item.checked ? 'on' : ''}" data-act="check">${item.checked ? '✓' : ''}</button>
        <input class="item-label" value="${esc(item.label)}" placeholder="To-do…" />
        <button class="icon-btn ${hasNotes ? 'has-notes' : ''}" data-act="notes" title="Notes">
          <svg viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M1 1l4 4 4-4"/></svg>
        </button>
        <button class="icon-btn" data-act="delete" title="Delete">✕</button>
      </div>
      <div class="notes-area ${item._notesOpen ? 'open' : ''}">
        <textarea placeholder="Notes…">${esc(item.notes || '')}</textarea>
      </div>`;
    return row;
  }

  function renderTimer(item, idx) {
    const row = document.createElement('div');
    const pct = item.totalSeconds > 0 ? Math.min(100, (item.elapsed / item.totalSeconds) * 100) : 0;
    const done = pct >= 100;
    row.className = 'item timer has-progress' + (done ? ' done' : '') + (item.running ? ' running' : '');
    row.dataset.idx = idx;
    row.setAttribute('draggable', 'true');
    const hasNotes = item.notes && item.notes.trim();
    row.innerHTML = `
      <div class="bar-fill" style="width:${pct}%"></div>
      <div class="playhead" style="left:${pct}%"></div>
      <div class="scrub-handle" style="left:${pct}%" title="Drag to scrub"></div>
      <div class="item-content">
        <button class="check-btn ${done ? 'on' : ''}" data-act="reset" title="${done ? 'Reset' : 'Clear'}">${done ? '✓' : ''}</button>
        <input class="item-label" value="${esc(item.label)}" placeholder="Timer…" />
        <button class="play-btn" data-act="play" title="${item.running ? 'Pause' : 'Start'}">${item.running ? '❚❚' : '▶'}</button>
        <div class="timer-display">
          <input class="time-input elapsed-input" value="${fmtTime(item.elapsed)}" data-act="elapsed" />
          <span style="opacity:.5">/</span>
          <input class="time-input total-input" value="${fmtTime(item.totalSeconds)}" data-act="total" />
          <span class="time-adjust">
            <button data-act="up" title="+30 min"><svg viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M1 5l4-4 4 4"/></svg></button>
            <button data-act="down" title="−30 min"><svg viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M1 1l4 4 4-4"/></svg></button>
          </span>
        </div>
        <button class="icon-btn ${hasNotes ? 'has-notes' : ''}" data-act="notes" title="Notes">
          <svg viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M1 1l4 4 4-4"/></svg>
        </button>
        <button class="icon-btn" data-act="delete" title="Delete">✕</button>
      </div>
      <div class="notes-area ${item._notesOpen ? 'open' : ''}">
        <textarea placeholder="Notes…">${esc(item.notes || '')}</textarea>
      </div>`;
    return row;
  }

  function wireRow(row, item) {
    row.addEventListener('click', e => {
      const act = e.target.closest('[data-act]')?.dataset.act;
      if (!act) return;
      if (act === 'check') { item.checked = !item.checked; save(); renderAll(); }
      if (act === 'reset') {
        if (item.elapsed >= item.totalSeconds) { item.elapsed = 0; item.running = false; stopInterval(item); save(); renderAll(); }
      }
      if (act === 'play') toggleTimer(item);
      if (act === 'delete') { stopInterval(item); items.splice(items.indexOf(item), 1); save(); renderAll(); }
      if (act === 'notes') { item._notesOpen = !item._notesOpen; renderAll(); }
      if (act === 'up') { item.totalSeconds += 1800; save(); renderAll(); }
      if (act === 'down') { item.totalSeconds = Math.max(0, item.totalSeconds - 1800); if (item.elapsed > item.totalSeconds) item.elapsed = item.totalSeconds; save(); renderAll(); }
    });
    row.querySelectorAll('input').forEach(inp => {
      inp.addEventListener('click', e => e.stopPropagation());
    });
    const label = row.querySelector('.item-label');
    label.addEventListener('input', e => { item.label = e.target.value; save(); });
    const el = row.querySelector('.elapsed-input');
    if (el) el.addEventListener('change', e => {
      const s = parseTime(e.target.value);
      if (s != null) { item.elapsed = Math.min(s, item.totalSeconds); save(); renderAll(); }
    });
    const tot = row.querySelector('.total-input');
    if (tot) tot.addEventListener('change', e => {
      const s = parseTime(e.target.value);
      if (s != null) { item.totalSeconds = s; save(); renderAll(); }
    });
    const ta = row.querySelector('.notes-area textarea');
    if (ta) {
      let t;
      ta.addEventListener('input', () => {
        item.notes = ta.value;
        clearTimeout(t); t = setTimeout(() => save(), 400);
      });
    }
    // Scrub handle
    const handle = row.querySelector('.scrub-handle');
    if (handle) attachScrub(row, item, handle);
  }

  function attachScrub(row, item, handle) {
    const startDrag = (e) => {
      if (e.button !== undefined && e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();
      const wasRunning = item.running;
      const getX = ev => (ev.touches && ev.touches[0] ? ev.touches[0].clientX : ev.clientX);
      if (wasRunning) { item.running = false; stopInterval(item); }
      const onMove = ev => {
        ev.preventDefault();
        const rect = row.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (getX(ev) - rect.left) / rect.width));
        item.elapsed = ratio * item.totalSeconds;
        updateTimerRow(row, item);
      };
      const onUp = () => {
        document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp);
        document.removeEventListener('touchmove', onMove); document.removeEventListener('touchend', onUp);
        const resume = wasRunning && item.elapsed < item.totalSeconds;
        if (resume) item.running = true;
        save(); renderAll();
        if (resume) startInterval(item);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend', onUp);
    };
    handle.addEventListener('mousedown', startDrag);
    handle.addEventListener('touchstart', startDrag, { passive: false });
  }

  // Drag & drop reorder
  let dragIdx = null;
  let dropIndicator = null;
  function ensureIndicator() {
    if (!dropIndicator) { dropIndicator = document.createElement('div'); dropIndicator.className = 'drop-indicator'; }
    return dropIndicator;
  }
  function wireDrag() {
    const list = listEl();
    list.querySelectorAll('.item').forEach(row => {
      row.addEventListener('dragstart', e => {
        if (e.target.closest('button, input, textarea, .notes-area, .scrub-handle')) { e.preventDefault(); return; }
        dragIdx = Number(row.dataset.idx);
        e.dataTransfer.effectAllowed = 'move';
        requestAnimationFrame(() => row.classList.add('dragging'));
      });
      row.addEventListener('dragend', () => {
        row.classList.remove('dragging'); dragIdx = null;
        const ind = ensureIndicator(); ind.classList.remove('visible');
        if (ind.parentNode) ind.parentNode.removeChild(ind);
      });
    });
    list.ondragover = e => {
      e.preventDefault(); if (dragIdx == null) return;
      const ind = ensureIndicator();
      const children = [...list.querySelectorAll('.item')];
      let before = null;
      for (const c of children) {
        const r = c.getBoundingClientRect();
        if (e.clientY < r.top + r.height/2) { before = c; break; }
      }
      if (before) list.insertBefore(ind, before); else list.appendChild(ind);
      ind.classList.add('visible');
    };
    list.ondrop = e => {
      e.preventDefault();
      const ind = ensureIndicator(); ind.classList.remove('visible');
      if (dragIdx == null) return;
      const children = [...list.querySelectorAll('.item')];
      let dropIdx = children.length;
      for (let i = 0; i < children.length; i++) {
        const r = children[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height/2) { dropIdx = i; break; }
      }
      const [moved] = items.splice(dragIdx, 1);
      const insertAt = dropIdx > dragIdx ? dropIdx - 1 : dropIdx;
      items.splice(insertAt, 0, moved);
      dragIdx = null;
      if (ind.parentNode) ind.parentNode.removeChild(ind);
      save(); renderAll();
    };
  }

  function renderAll() {
    const list = listEl();
    list.innerHTML = '';
    items.forEach((item, idx) => {
      const row = item.type === 'timer' ? renderTimer(item, idx) : renderTodo(item, idx);
      wireRow(row, item);
      list.appendChild(row);
    });
    wireDrag();
    const totalMin = items.filter(i => i.type === 'timer').reduce((s,i) => s + i.totalSeconds, 0) / 60;
    document.getElementById('today-meta').textContent = totalMin > 0 ? `· ${(totalMin/60).toFixed(1)} hrs planned` : '';
    updateRunningIndicator();
  }

  // Backlog
  function renderBacklog() {
    const el = document.getElementById('backlog');
    el.innerHTML = '';
    backlog.forEach((t, i) => {
      const row = document.createElement('div');
      row.className = 'backlog-item' + (t.done ? ' done' : '');
      row.innerHTML = `
        <button class="check-btn ${t.done ? 'on' : ''}" data-act="check">${t.done ? '✓' : ''}</button>
        <input class="title" value="${esc(t.title)}" />
        ${t.due ? `<span class="due ${t.overdue ? 'overdue' : ''}">${t.due}</span>` : ''}
        <button class="icon-btn" data-act="del">✕</button>`;
      row.addEventListener('click', e => {
        const act = e.target.closest('[data-act]')?.dataset.act;
        if (act === 'check') { t.done = !t.done; saveBacklog(); renderBacklog(); }
        if (act === 'del')   { backlog.splice(i, 1); saveBacklog(); renderBacklog(); }
      });
      row.querySelector('.title').addEventListener('input', e => { t.title = e.target.value; saveBacklog(); });
      el.appendChild(row);
    });
  }

  // Archive done items
  function archiveAllDone() {
    const isDone = i => (i.type === 'todo' && i.checked) || (i.type === 'timer' && i.totalSeconds > 0 && i.elapsed >= i.totalSeconds);
    items = items.filter(i => { if (isDone(i)) { stopInterval(i); return false; } return true; });
    save(); renderAll();
  }

  // Add buttons
  document.getElementById('todo-btn').onclick = () => {
    items.push({ type: 'todo', label: '', checked: false, notes: '' });
    save(); renderAll();
    const last = document.querySelector('#list .item:last-child .item-label');
    if (last) last.focus();
  };
  document.getElementById('timer-btn').onclick = () => {
    items.push({ type: 'timer', label: '', totalSeconds: 1800, elapsed: 0, running: false, notes: '' });
    save(); renderAll();
    const last = document.querySelector('#list .item:last-child .item-label');
    if (last) last.focus();
  };
  document.getElementById('archive-btn').onclick = archiveAllDone;
  document.getElementById('voice-btn').onclick = () => {
    const b = document.getElementById('voice-btn');
    b.classList.toggle('recording');
    b.textContent = b.classList.contains('recording') ? '⏹ Stop' : '+ Voice';
  };
  document.getElementById('backlog-add').onclick = () => {
    backlog.unshift({ title: 'New task', done: false });
    saveBacklog(); renderBacklog();
  };
  document.getElementById('backlog-refresh').onclick = renderBacklog;

  // Resume timers on load
  function resume() { items.forEach(i => { if (i.type === 'timer' && i.running) startInterval(i); }); }

  // Init
  window.__DUSK = window.__DUSK || { phaseOverride: null, muteBell: false };
  seedIfEmpty();
  seedBacklogIfEmpty();
  renderAll();
  renderBacklog();
  resume();
  tickClock();
  setInterval(tickClock, 1000);

  // Expose for tweaks panel
  window.__DUSK_REFRESH_CLOCK = tickClock;
})();
