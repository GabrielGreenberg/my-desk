// dusk-tweaks.jsx — Tweaks panel with hue dial + phase override + bell mute.

const DUSK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "hue": 30,
  "phase": "auto",
  "muteBell": false
}/*EDITMODE-END*/;

function HueDial({ value, onChange }) {
  const size = 140;
  const radius = size / 2 - 14;
  const cx = size / 2, cy = size / 2;
  const angle = (value - 90) * Math.PI / 180;
  const hx = cx + Math.cos(angle) * radius;
  const hy = cy + Math.sin(angle) * radius;

  const dragging = React.useRef(false);
  const svgRef = React.useRef(null);

  const updateFromEvent = (e) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left - cx;
    const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top - cy;
    let deg = Math.round(Math.atan2(y, x) * 180 / Math.PI + 90);
    if (deg < 0) deg += 360;
    onChange(deg % 360);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <svg
        ref={svgRef}
        width={size} height={size} viewBox={`0 0 ${size} ${size}`}
        style={{ cursor: 'grab', touchAction: 'none' }}
        onMouseDown={(e) => { dragging.current = true; updateFromEvent(e); }}
        onMouseMove={(e) => { if (dragging.current) updateFromEvent(e); }}
        onMouseUp={() => dragging.current = false}
        onMouseLeave={() => dragging.current = false}
        onTouchStart={(e) => { dragging.current = true; updateFromEvent(e); }}
        onTouchMove={(e) => { if (dragging.current) { e.preventDefault(); updateFromEvent(e); } }}
        onTouchEnd={() => dragging.current = false}
      >
        <defs>
          <radialGradient id="dialRing">
            <stop offset="0" stopColor="rgba(0,0,0,0)" />
            <stop offset="0.75" stopColor="rgba(0,0,0,0)" />
            <stop offset="0.76" stopColor="rgba(0,0,0,0.25)" />
            <stop offset="1" stopColor="rgba(0,0,0,0.25)" />
          </radialGradient>
        </defs>
        {/* Hue wheel */}
        <foreignObject x="0" y="0" width={size} height={size}>
          <div style={{
            width: size, height: size, borderRadius: '50%',
            background: `conic-gradient(from 0deg,
              oklch(0.7 0.16 0), oklch(0.7 0.16 60),
              oklch(0.7 0.16 120), oklch(0.7 0.16 180),
              oklch(0.7 0.16 240), oklch(0.7 0.16 300),
              oklch(0.7 0.16 360))`,
          }} />
        </foreignObject>
        {/* Inner hole */}
        <circle cx={cx} cy={cy} r={radius - 14} fill="var(--bg-solid, #222)" />
        {/* Knob indicator */}
        <circle cx={hx} cy={hy} r="8" fill="white" stroke="rgba(0,0,0,0.4)" strokeWidth="1.5" />
        <circle cx={hx} cy={hy} r="4" fill={`oklch(0.65 0.17 ${value})`} />
        {/* Center value */}
        <text x={cx} y={cy - 2} textAnchor="middle" fontFamily="Geist, system-ui, sans-serif"
              fontSize="14" fill="var(--text)" fontWeight="500" style={{fontVariantNumeric: 'tabular-nums'}}>{value}°</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontFamily="Geist, sans-serif"
              fontSize="8" fill="var(--text-dim)" letterSpacing="1.5" textTransform="uppercase">HUE</text>
      </svg>
    </div>
  );
}

function DuskTweaks() {
  const { useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakToggle } = window;
  const [t, setTweak] = useTweaks(DUSK_DEFAULTS);

  // Apply theme whenever hue or phase changes
  React.useEffect(() => {
    const applyTheme = () => {
      let phase;
      if (t.phase === 'auto') {
        phase = window.duskPhaseForHour(new Date().getHours());
      } else {
        const preset = window.DUSK_PRESETS[t.phase];
        phase = window.duskPhaseForHour(preset ? preset.hour : new Date().getHours());
      }
      window.applyDuskTheme(phase, t.hue);
      window.__DUSK = window.__DUSK || {};
      window.__DUSK.phaseOverride = t.phase === 'auto' ? null
        : window.DUSK_PRESETS[t.phase]?.hour ?? null;
      window.__DUSK.muteBell = !!t.muteBell;
      if (window.__DUSK_REFRESH_CLOCK) window.__DUSK_REFRESH_CLOCK();
    };
    applyTheme();
    // Re-apply every minute for auto mode so phase transitions naturally.
    if (t.phase === 'auto') {
      const id = setInterval(applyTheme, 60 * 1000);
      return () => clearInterval(id);
    }
  }, [t.hue, t.phase, t.muteBell]);

  return (
    <TweaksPanel>
      <TweakSection label="Ambient" />
      <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0 2px' }}>
        <HueDial value={t.hue} onChange={v => setTweak('hue', v)} />
      </div>
      <div style={{
        fontSize: 10, color: 'rgba(41,38,27,.55)', textAlign: 'center',
        letterSpacing: 0.3, marginTop: -2,
      }}>The whole palette shifts as you turn.</div>

      <TweakSection label="Time of day" />
      <TweakRadio
        value={t.phase}
        options={['auto', 'dawn', 'afternoon', 'goldenHour', 'night']}
        onChange={v => setTweak('phase', v)}
      />

      <TweakSection label="Sound" />
      <TweakToggle label="Mute bell on timer end" value={t.muteBell}
                   onChange={v => setTweak('muteBell', v)} />
    </TweaksPanel>
  );
}

// Apply initial theme immediately so FOUC is minimal
window.applyDuskTheme(
  window.duskPhaseForHour(new Date().getHours()),
  DUSK_DEFAULTS.hue
);

const __tweaksRoot = document.createElement('div');
document.body.appendChild(__tweaksRoot);
ReactDOM.createRoot(__tweaksRoot).render(<DuskTweaks />);
