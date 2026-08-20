/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ChartColor } from '../colors'

export interface DonutSlice {
  /** Stable key for the slice (used as the render key). */
  key: string
  /** Localized label shown in the legend. */
  label: string
  /** Numeric weight of the slice; percentages are derived from the sum of all values. */
  value: number
  /** Named palette color of the slice arc and its legend swatch. */
  color: ChartColor
}

/** One legend row, formatted by the chart so the legend holds no arithmetic. */
export interface DonutLegendRow {
  key: string
  label: string
  color: ChartColor
  hidden: boolean
  /** Share of the ring, or a dash for a category the ring is not drawn over. */
  shareText: string
}

export interface CmkDonutChartProps {
  /**
   * Slices in display order. The caller provides them pre-ranked and already
   * includes any aggregated "Other" slice; percentages are computed from the
   * sum of all slice values.
   */
  slices: DonutSlice[]
  /** The chart does not know what its values measure, so the caller formats. */
  formatValue: (value: number) => string
  /** Defaults to "Volume". */
  centerLabel?: string
}
