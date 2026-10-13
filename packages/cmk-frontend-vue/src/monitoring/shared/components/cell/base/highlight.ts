/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type CellHighlightColor =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'unknown'
  | 'pending'

export interface CellHighlight {
  color: CellHighlightColor
  minWidth?: number | undefined
  /**
   * Set to false to keep the highlight's layout (accent bar space, minWidth) for alignment
   * purposes, without showing its color — e.g. a zero count next to non-zero, colored counts.
   */
  active?: boolean | undefined
}
