/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How a cell turns into what the reader sees. `delta` draws an arrow along the
 * sign of the cell's value and writes its `formatted` text beside it; a value
 * of zero is no change and gets no arrow.
 */
export type RankedTableCellRender = 'text' | 'bytes' | 'count' | 'delta'

export interface RankedTableColumn {
  key: string
  title: string
  render: RankedTableCellRender
  bar: boolean
  /** When true, cells render as buttons emitting `cellClick`. Ignored for bar columns. */
  clickable?: boolean
  /**
   * Fixed `[minimum, maximum]` used to scale this column's bars, clamped to that range.
   * Defaults to `0..largest value in the column`. Only meaningful for bar columns.
   */
  barRange?: [number, number]
}

/**
 * A cell carrying display overrides. Cells may also be given as a bare value, which is
 * equivalent to `{ value }`.
 */
export interface RankedTableCell {
  value: string | number
  /** Ready-to-display text, taking precedence over the column's `render` formatting. */
  formatted?: string
  /** Renders the cell as a link. Takes precedence over `clickable`. */
  href?: string
  /** CSS color overriding `barColor` for this row's bar. */
  color?: string
}

export type RankedTableRow = Record<string, string | number | RankedTableCell>

export interface CmkRankedTableProps {
  columns: RankedTableColumn[]
  /** Rows in display order (the caller provides them pre-ranked). */
  rows: RankedTableRow[]
  /** CSS color used to fill the inline bars. A cell's own `color` overrides it. */
  barColor?: string
}
