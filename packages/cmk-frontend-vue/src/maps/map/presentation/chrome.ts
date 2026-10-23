/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Static chrome for the presentation editor: its toolbar glyphs and the
// slide-size presets.
//
// These are the design-tool vocabulary -- shapes, alignment, layers, connect --
// which Checkmk's own icon set does not carry, so they are inline SVG rather
// than ``CmkIcon``. They render through ``PresentationGlyph``, the one reviewed
// v-html sink, and never come from user or backend data.

export const ICONS = {
  rect: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="6" width="16" height="12" rx="2"/></svg>',
  ellipse:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="12" rx="8" ry="6"/></svg>',
  line: '<svg width="18" height="18" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="4" y1="18" x2="20" y2="6"/></svg>',
  arrow:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="12" x2="18" y2="12"/><polyline points="13,7 19,12 13,17"/></svg>',
  text: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 6h14M12 6v12"/></svg>',
  image:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="1.5"/><path d="M21 16l-5-5L5 19"/></svg>',
  data: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v18M3 8l9 5 9-5"/></svg>',
  layers:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></svg>',
  database:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></svg>',
  plug: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0z"/><path d="M12 16v5"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
  unlock:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  eyeOff:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.9 5A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a18 18 0 0 1-3 3.7M6 6.3A18 18 0 0 0 2 12s3.5 7 10 7a10.3 10.3 0 0 0 5-1.3"/><path d="M3 3l18 18"/></svg>',
  save: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>',
  duplicate:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
  trash:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-9 0v12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V7"/></svg>',
  undo: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 7L4 12l5 5"/><path d="M4 12h11a5 5 0 0 1 0 10h-1"/></svg>',
  redo: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 7l5 5-5 5"/><path d="M20 12H9a5 5 0 0 0 0 10h1"/></svg>',
  previous:
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15,5 8,12 15,19"/></svg>',
  next: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9,5 16,12 9,19"/></svg>',
  alignL:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 4v16M8 8h8M8 16h5"/></svg>',
  alignC:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M12 4v16M7 8h10M9 16h6"/></svg>',
  alignR:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M20 4v16M8 8h8M11 16h5"/></svg>',
  alignT:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 4h16M8 8v8M16 8v5"/></svg>',
  alignM:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 12h16M8 7v10M16 9v6"/></svg>',
  alignB:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 20h16M8 8v8M16 11v5"/></svg>',
  distH:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 4v16M20 4v16M11 8v8"/></svg>',
  distV:
    '<svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M4 4h16M4 20h16M8 11h8"/></svg>'
}

export const SLIDE_PRESETS: { label: string; w: number; h: number }[] = [
  { label: '16:9', w: 1920, h: 1080 },
  { label: '16:10', w: 1920, h: 1200 },
  { label: '4:3', w: 1440, h: 1080 },
  { label: '21:9', w: 2560, h: 1080 },
  { label: '9:16', w: 1080, h: 1920 },
  { label: '720p', w: 1280, h: 720 }
]
