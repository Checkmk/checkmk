/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ContextualLinkEntry } from '@/dashboard/lib/contextualLinkUrl'

/** How a cell turns into what the reader sees. */
export type RankedTableCellRender = 'text' | 'count'

export interface RankedTableColumn {
  key: string
  title: string
  render: RankedTableCellRender
  bar: boolean
  /** `secondary` sets the column's text and links in a quieter style. */
  tone?: 'primary' | 'secondary'
  /**
   * Fixed `[minimum, maximum]` used to scale this column's bars, clamped to that range.
   * Defaults to `0..largest value in the column`. Only meaningful for bar columns.
   */
  barRange?: [number, number]
}

interface RankedTableCellBase {
  value: string | number
  /** Ready-to-display text, taking precedence over the column's `render` formatting. */
  formatted?: string
  /** CSS color overriding the default bar color for this row's bar. */
  color?: string
  /** Shown quietly after the value. */
  unit?: string | undefined
}

/**
 * A cell carrying display overrides. Cells may also be given as a bare value, which is
 * equivalent to `{ value }`.
 */
export type RankedTableCell = RankedTableCellBase &
  (
    | {
        /** Renders the cell as a link. */
        href?: string
        choices?: never
      }
    | {
        /** Renders the cell as a menu of several links. */
        choices: ContextualLinkEntry[]
        href?: never
      }
  )

export type RankedTableRow = Record<string, string | number | RankedTableCell>

/**
 * Stand-in rows in the table's columns: `loading` animates them, `empty` shows them faded
 * behind the `empty` slot.
 */
export interface RankedTablePlaceholder {
  kind: 'loading' | 'empty'
  rows: number
}

export interface CmkRankedTableProps {
  columns: RankedTableColumn[]
  /** Rows in display order (the caller provides them pre-ranked). */
  rows: RankedTableRow[]
  /** Replaces the rows with stand-ins. */
  placeholder?: RankedTablePlaceholder | undefined
  /** Whether newer rows are being fetched, which assistive tech is told. */
  busy?: boolean
  /** Prepends each row's position, starting at 1. */
  showRank?: boolean
  /** Accessible name of the table, e.g. the widget title. */
  label?: string | undefined
  /**
   * Identifies a row across updates, so that a refresh animates each row from its own previous
   * value and keyboard focus follows it when it moves. Defaults to the row's position.
   */
  rowKey?: (row: RankedTableRow, index: number) => string
}
