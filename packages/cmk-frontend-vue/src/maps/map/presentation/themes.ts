/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PresentationTheme } from '@/maps/types/api'

// A theme is a CSS-variable token set applied inline on the slide root, so
// shapes and text default to a coherent palette without per-element styling.
// Element insert-defaults pull from the active theme (see elementDefaults).
// The index signature lets the tokens spread directly into a CSS-var style
// object without casting.
export interface PresentationThemeTokens extends Record<string, string> {
  '--pres-bg': string
  '--pres-fg': string
  '--pres-muted': string
  '--pres-accent': string
  '--pres-panel': string
  '--pres-shape-fill': string
  '--pres-shape-stroke': string
  '--pres-font': string
  '--pres-font-display': string
}

export interface PresentationThemeMeta {
  id: PresentationTheme
  title: string
  tokens: PresentationThemeTokens
}

export const PRESENTATION_THEMES: Record<PresentationTheme, PresentationThemeMeta> = {
  midnight: {
    id: 'midnight',
    title: 'Midnight',
    tokens: {
      '--pres-bg': '#0b1020',
      '--pres-fg': '#e5e7eb',
      '--pres-muted': '#7c89a8',
      '--pres-accent': '#38bdf8',
      '--pres-panel': '#151c30',
      '--pres-shape-fill': '#1e2a44',
      '--pres-shape-stroke': '#38bdf8',
      '--pres-font': 'ui-sans-serif, system-ui, sans-serif',
      '--pres-font-display': "'Trebuchet MS', ui-sans-serif, system-ui, sans-serif"
    }
  },
  paper: {
    id: 'paper',
    title: 'Paper',
    tokens: {
      '--pres-bg': '#f4efe3',
      '--pres-fg': '#23201a',
      '--pres-muted': '#8a8170',
      '--pres-accent': '#b45309',
      '--pres-panel': '#ece4d3',
      '--pres-shape-fill': '#e2d8c2',
      '--pres-shape-stroke': '#b45309',
      '--pres-font': "'Iowan Old Style', Georgia, ui-serif, serif",
      '--pres-font-display': "'Iowan Old Style', Georgia, ui-serif, serif"
    }
  },
  ops: {
    id: 'ops',
    title: 'Ops',
    tokens: {
      '--pres-bg': '#050607',
      '--pres-fg': '#f8fafc',
      '--pres-muted': '#5b7060',
      '--pres-accent': '#22c55e',
      '--pres-panel': '#0d1410',
      '--pres-shape-fill': '#0f1c14',
      '--pres-shape-stroke': '#22c55e',
      '--pres-font': "ui-monospace, 'Cascadia Code', Menlo, monospace",
      '--pres-font-display': "ui-monospace, 'Cascadia Code', Menlo, monospace"
    }
  },
  aurora: {
    id: 'aurora',
    title: 'Aurora',
    tokens: {
      '--pres-bg': '#191033',
      '--pres-fg': '#f0e9ff',
      '--pres-muted': '#9d8fc4',
      '--pres-accent': '#c084fc',
      '--pres-panel': '#241647',
      '--pres-shape-fill': '#2e1d5c',
      '--pres-shape-stroke': '#c084fc',
      '--pres-font': 'ui-sans-serif, system-ui, sans-serif',
      '--pres-font-display': "'Trebuchet MS', ui-sans-serif, system-ui, sans-serif"
    }
  }
}

export function themeTokens(theme: PresentationTheme): PresentationThemeTokens {
  return (PRESENTATION_THEMES[theme] ?? PRESENTATION_THEMES.midnight).tokens
}

export function themeOptions(): { name: PresentationTheme; title: string }[] {
  return Object.values(PRESENTATION_THEMES).map((t) => ({ name: t.id, title: t.title }))
}
