// Shared demo data for all four design directions.
// Mirrors the shape of the real app's items.
window.DEMO_ITEMS = [
  { type: 'timer', label: 'Grading admin',      totalSeconds: 3600, elapsed: 3600, running: false, checked: true },
  { type: 'timer', label: 'Reading finals',     totalSeconds: 3600, elapsed: 1980, running: true },
  { type: 'timer', label: 'Email',              totalSeconds: 1800, elapsed: 0 },
  { type: 'todo',  label: 'Reply to Marcus re: syllabus', checked: false },
  { type: 'timer', label: 'MIT: Image paper',   totalSeconds: 1800, elapsed: 420 },
  { type: 'todo',  label: 'Weekend planning',   checked: false, hasNotes: true },
  { type: 'timer', label: 'Messaging',          totalSeconds: 1800, elapsed: 0 },
];

window.DEMO_BACKLOG = [
  { title: 'Draft intro for vision paper',         due: 'Today',    done: false, overdue: false },
  { title: 'Review Jana\u2019s revisions',              due: 'Tomorrow', done: false, overdue: false },
  { title: 'Book flights for May conference',      due: 'Thu',      done: false, overdue: false },
  { title: 'Submit expense report',                due: 'Apr 18',   done: false, overdue: true },
  { title: 'Sketch outline for seminar talk',      done: false },
  { title: 'Pick up dry cleaning',                 done: true },
];

// Helper: mm:ss formatter
window.fmtTime = function(sec) {
  sec = Math.round(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
};

window.fmtClock = function(date = new Date()) {
  return date.toLocaleTimeString('en-US', { hour12: true, hour: 'numeric', minute: '2-digit' });
};

window.fmtDate = function(date = new Date()) {
  return date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};
