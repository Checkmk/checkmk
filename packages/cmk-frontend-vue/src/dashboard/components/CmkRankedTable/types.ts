/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/** How a cell turns into what the reader sees. */
export type RankedTableCellRender = 'text' | 'count'

export interface RankedTableColumn {
  key: string
  title: string
  render: RankedTableCellRender
  bar: boolean
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
  /** Renders the cell as a link. */
  href?: string
  /** CSS color overriding the default bar color for this row's bar. */
  color?: string
}

export type RankedTableRow = Record<string, string | number | RankedTableCell>

export interface CmkRankedTableProps {
  columns: RankedTableColumn[]
  /** Rows in display order (the caller provides them pre-ranked). */
  rows: RankedTableRow[]
}
