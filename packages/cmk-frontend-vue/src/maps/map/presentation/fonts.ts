/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Curated font stacks for the presentation inspector's typography section.
// Every stack must pass the backend's _FONT_RE (letters, digits, space, comma,
// quotes, hyphen, dot only) — no parentheses, colons or braces.
export interface PresentationFontOption {
  // null = inherit the slide theme's font.
  stack: string | null
  title: string
}

export const PRESENTATION_FONTS: PresentationFontOption[] = [
  { stack: null, title: 'Theme default' },
  { stack: 'ui-sans-serif, system-ui, sans-serif', title: 'Sans' },
  { stack: "'Trebuchet MS', ui-sans-serif, sans-serif", title: 'Trebuchet' },
  { stack: "'Iowan Old Style', Georgia, ui-serif, serif", title: 'Serif' },
  { stack: "'Times New Roman', Times, serif", title: 'Times' },
  { stack: "ui-monospace, 'Cascadia Code', Menlo, Consolas, monospace", title: 'Mono' },
  { stack: "'Arial Narrow', 'Helvetica Neue', Arial, sans-serif", title: 'Condensed' },
  { stack: "Impact, 'Arial Black', sans-serif", title: 'Display' }
]
