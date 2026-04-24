// dusk-theme.jsx — palette + time-of-day + hue application to CSS vars

window.DUSK_PRESETS = {
  auto:       { label: 'Auto (by time of day)' },
  dawn:       { label: 'Dawn',        hour:  7 },
  afternoon:  { label: 'Afternoon',   hour: 14 },
  goldenHour: { label: 'Golden hour', hour: 19 },
  night:      { label: 'Night',       hour: 23 },
};

// Returns the phase key ('dawn'|'day'|'dusk'|'night') for a given hour.
window.duskPhaseForHour = function(hour) {
  if (hour >= 5  && hour < 9)  return 'dawn';
  if (hour >= 9  && hour < 17) return 'day';
  if (hour >= 17 && hour < 21) return 'dusk';
  return 'night';
};

window.duskPhaseLabel = function(phase) {
  return { dawn: 'dawn', day: 'afternoon', dusk: 'golden hour', night: 'night' }[phase];
};

// Build a palette for a phase + a central accent hue (0-360).
// All lightness/chroma is fixed per phase, only hue shifts — so the whole UI
// re-tints coherently when the dial moves.
window.duskPalette = function(phase, hue) {
  const H = hue;
  // base backgrounds per phase — use accent hue subtly in gradient stops
  const paletteByPhase = {
    dawn: {
      bg: `linear-gradient(180deg,
             oklch(0.88 0.06 ${(H+10)%360}) 0%,
             oklch(0.82 0.05 ${(H+330)%360}) 45%,
             oklch(0.74 0.055 ${(H+280)%360}) 100%)`,
      bgSolid:   `oklch(0.85 0.04 ${H})`,
      text:      `oklch(0.24 0.03 ${(H+260)%360})`,
      textDim:   `oklch(0.42 0.025 ${(H+260)%360})`,
      textMute:  `oklch(0.55 0.02 ${(H+260)%360})`,
      surface:   `oklch(0.98 0.01 ${H} / 0.58)`,
      surfaceHi: `oklch(0.99 0.01 ${H} / 0.82)`,
      border:    `oklch(0.24 0.03 ${(H+260)%360} / 0.12)`,
      borderHi:  `oklch(0.24 0.03 ${(H+260)%360} / 0.22)`,
      accent:    `oklch(0.58 0.15 ${H})`,
      accentMid: `oklch(0.65 0.12 ${H})`,
      accentGlow:`oklch(0.75 0.18 ${H} / 0.35)`,
      barFill:   `oklch(0.42 0.12 ${H} / 0.55)`,
      barDone:   `oklch(0.42 0.06 ${H} / 0.28)`,
    },
    day: {
      bg: `linear-gradient(180deg,
             oklch(0.86 0.035 ${(H+200)%360}) 0%,
             oklch(0.88 0.03 ${H}) 55%,
             oklch(0.84 0.045 ${(H+20)%360}) 100%)`,
      bgSolid:   `oklch(0.87 0.03 ${H})`,
      text:      `oklch(0.22 0.02 ${(H+240)%360})`,
      textDim:   `oklch(0.42 0.02 ${(H+240)%360})`,
      textMute:  `oklch(0.56 0.015 ${(H+240)%360})`,
      surface:   `oklch(0.99 0.005 ${H} / 0.62)`,
      surfaceHi: `oklch(1.00 0.005 ${H} / 0.85)`,
      border:    `oklch(0.22 0.02 ${(H+240)%360} / 0.10)`,
      borderHi:  `oklch(0.22 0.02 ${(H+240)%360} / 0.20)`,
      accent:    `oklch(0.52 0.15 ${H})`,
      accentMid: `oklch(0.60 0.12 ${H})`,
      accentGlow:`oklch(0.72 0.16 ${H} / 0.28)`,
      barFill:   `oklch(0.40 0.13 ${H} / 0.55)`,
      barDone:   `oklch(0.40 0.06 ${H} / 0.26)`,
    },
    dusk: {
      bg: `linear-gradient(180deg,
             oklch(0.75 0.14 ${H}) 0%,
             oklch(0.55 0.14 ${(H+340)%360}) 45%,
             oklch(0.35 0.08 ${(H+290)%360}) 90%,
             oklch(0.24 0.05 ${(H+280)%360}) 100%)`,
      bgSolid:   `oklch(0.30 0.06 ${(H+290)%360})`,
      text:      `oklch(0.94 0.025 ${H})`,
      textDim:   `oklch(0.72 0.03 ${H})`,
      textMute:  `oklch(0.56 0.03 ${H})`,
      surface:   `oklch(0.22 0.04 ${(H+280)%360} / 0.55)`,
      surfaceHi: `oklch(0.28 0.05 ${(H+280)%360} / 0.80)`,
      border:    `oklch(0.94 0.025 ${H} / 0.14)`,
      borderHi:  `oklch(0.94 0.025 ${H} / 0.30)`,
      accent:    `oklch(0.80 0.17 ${H})`,
      accentMid: `oklch(0.72 0.15 ${H})`,
      accentGlow:`oklch(0.78 0.20 ${H} / 0.45)`,
      barFill:   `oklch(0.70 0.14 ${H} / 0.55)`,
      barDone:   `oklch(0.70 0.08 ${H} / 0.25)`,
    },
    night: {
      bg: `linear-gradient(180deg,
             oklch(0.18 0.04 ${(H+230)%360}) 0%,
             oklch(0.22 0.05 ${(H+260)%360}) 55%,
             oklch(0.16 0.04 ${(H+220)%360}) 100%)`,
      bgSolid:   `oklch(0.18 0.04 ${(H+230)%360})`,
      text:      `oklch(0.92 0.02 ${H})`,
      textDim:   `oklch(0.68 0.02 ${H})`,
      textMute:  `oklch(0.50 0.02 ${H})`,
      surface:   `oklch(0.25 0.04 ${(H+240)%360} / 0.55)`,
      surfaceHi: `oklch(0.32 0.05 ${(H+240)%360} / 0.80)`,
      border:    `oklch(0.92 0.02 ${H} / 0.10)`,
      borderHi:  `oklch(0.92 0.02 ${H} / 0.24)`,
      accent:    `oklch(0.78 0.15 ${H})`,
      accentMid: `oklch(0.70 0.13 ${H})`,
      accentGlow:`oklch(0.72 0.16 ${H} / 0.30)`,
      barFill:   `oklch(0.68 0.13 ${H} / 0.52)`,
      barDone:   `oklch(0.68 0.07 ${H} / 0.22)`,
    },
  };
  return paletteByPhase[phase];
};

// Apply a palette to CSS custom properties on <html>.
window.applyDuskTheme = function(phase, hue) {
  const p = window.duskPalette(phase, hue);
  const r = document.documentElement.style;
  r.setProperty('--bg', p.bg);
  r.setProperty('--bg-solid', p.bgSolid);
  r.setProperty('--text', p.text);
  r.setProperty('--text-dim', p.textDim);
  r.setProperty('--text-mute', p.textMute);
  r.setProperty('--surface', p.surface);
  r.setProperty('--surface-hi', p.surfaceHi);
  r.setProperty('--border', p.border);
  r.setProperty('--border-hi', p.borderHi);
  r.setProperty('--accent', p.accent);
  r.setProperty('--accent-mid', p.accentMid);
  r.setProperty('--accent-glow', p.accentGlow);
  r.setProperty('--bar-fill', p.barFill);
  r.setProperty('--bar-done', p.barDone);

  const meta = document.querySelector('meta[name="theme-color"]:not([media])');
  if (meta) meta.setAttribute('content', p.bgSolid);
};
