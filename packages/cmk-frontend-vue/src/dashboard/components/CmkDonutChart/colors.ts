/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type ChartColor =
  | 'blue'
  | 'brown'
  | 'cyan'
  | 'green'
  | 'grey'
  | 'magenta'
  | 'orange'
  | 'purple'
  | 'red'
  | 'yellow'

export const CHART_COLOR_CSS: Record<ChartColor, string> = {
  blue: 'var(--series-color-9)',
  brown: 'var(--series-color-7)',
  cyan: 'var(--series-color-6)',
  green: 'var(--series-color-2)',
  grey: 'var(--series-color-11)',
  magenta: 'var(--series-color-8)',
  orange: 'var(--series-color-3)',
  purple: 'var(--series-color-5)',
  red: 'var(--series-color-4)',
  yellow: 'var(--series-color-10)'
}

// The literal hex behind every CHART_COLOR_CSS entry, for canvas renderers.
export const CHART_COLOR_HEX: Record<ChartColor, string> = {
  blue: '#28a2f3',
  brown: '#bf8548',
  cyan: '#1ee6e6',
  green: '#15d1a0',
  grey: '#7e8a95',
  magenta: '#ec48b6',
  orange: '#ff8400',
  purple: '#8380ff',
  red: '#ed3b3b',
  yellow: '#ffd703'
}

// Red, green and yellow are omitted because they carry state meaning elsewhere
// in Checkmk; grey is reserved for the "Other" tail and the empty state.
export const CATEGORICAL_PALETTE: ChartColor[] = [
  'blue',
  'purple',
  'cyan',
  'magenta',
  'orange',
  'brown'
]

export function chartColorCss(color: ChartColor): string {
  return CHART_COLOR_CSS[color]
}

export function chartColorHex(color: ChartColor): string {
  return CHART_COLOR_HEX[color]
}
