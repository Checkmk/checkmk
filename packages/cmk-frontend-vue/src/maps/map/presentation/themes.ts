/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { PresentationTheme } from '@/maps/types/api'

// A theme is a CSS-variable token set applied inline on the slide root, so
// shapes and text default to a coherent palette without per-element styling.
// The colours are Checkmk palette colours, spelled out as hex because the
// inspector's native colour picker takes its default from them.
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
      '--pres-bg': '#0f1215',
      '--pres-fg': '#ffffff',
      '--pres-muted': '#99a5ac',
      '--pres-accent': '#28a2f3',
      '--pres-panel': '#262e36',
      '--pres-shape-fill': '#303946',
      '--pres-shape-stroke': '#28a2f3'
    }
  },
  paper: {
    id: 'paper',
    title: 'Paper',
    tokens: {
      '--pres-bg': '#fbfbfe',
      '--pres-fg': '#1e262e',
      '--pres-muted': '#677883',
      '--pres-accent': '#0667c1',
      '--pres-panel': '#f0f0f4',
      '--pres-shape-fill': '#e0e0e4',
      '--pres-shape-stroke': '#0667c1'
    }
  },
  ops: {
    id: 'ops',
    title: 'Ops',
    tokens: {
      '--pres-bg': '#1c2228',
      '--pres-fg': '#ffffff',
      '--pres-muted': '#85939c',
      '--pres-accent': '#15d1a0',
      '--pres-panel': '#20272e',
      '--pres-shape-fill': '#252c36',
      '--pres-shape-stroke': '#15d1a0'
    }
  },
  aurora: {
    id: 'aurora',
    title: 'Aurora',
    tokens: {
      '--pres-bg': '#021f3b',
      '--pres-fg': '#ffffff',
      '--pres-muted': '#8cb9e2',
      '--pres-accent': '#53b5f5',
      '--pres-panel': '#032b51',
      '--pres-shape-fill': '#03396a',
      '--pres-shape-stroke': '#53b5f5'
    }
  }
}

export function themeTokens(theme: PresentationTheme): PresentationThemeTokens {
  return (PRESENTATION_THEMES[theme] ?? PRESENTATION_THEMES.midnight).tokens
}

export function themeOptions(): { name: PresentationTheme; title: string }[] {
  return Object.values(PRESENTATION_THEMES).map((t) => ({ name: t.id, title: t.title }))
}
