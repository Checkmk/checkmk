/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ChartColor } from '@/network-flow/colors'

export type RankedTableCellRender = 'text' | 'bytes' | 'count'

export interface RankedTableColumn {
  key: string
  title: string
  render: RankedTableCellRender
  bar: boolean
  /** When true, cells render as buttons emitting `cellClick`. Ignored for bar columns. */
  clickable?: boolean
}

export type RankedTableRow = Record<string, string | number>

export interface CmkRankedTableProps {
  columns: RankedTableColumn[]
  /** Rows in display order (the caller provides them pre-ranked). */
  rows: RankedTableRow[]
  /** Named palette color used to fill the inline bars. */
  barColor: ChartColor
}
