/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What an increase of the metric means, driving the delta indicator's color.
 * Neutral metrics (e.g. traffic volume) render the delta in a plain foreground
 * color; for good/bad metrics the direction is judged against the semantics.
 */
export type DeltaSemantics = 'neutral' | 'good' | 'bad'

/** Monitoring state of whatever the value was measured on. */
export type KpiStateSeverity = 'ok' | 'warn' | 'crit' | 'unknown' | 'pending'

export interface KpiState {
  severity: KpiStateSeverity
  /** Additionally tints the whole card in the state's color. */
  tintBackground?: boolean
}

/** Ends of the displayed value range, pre-formatted with the metric's unit. */
export interface KpiRangeLimits {
  minimum: string
  maximum: string
}

export interface CmkKpiStatCardProps {
  /** Pre-formatted headline value, e.g. "801.84" or "4.3". */
  value: string
  /** Unit rendered after the value, e.g. "GB" or "K"; omit for plain counts. */
  unit?: string | undefined
  /**
   * Change versus the previous period as a signed ratio (0.062 = up 6.2%).
   * Omit to hide the delta indicator entirely.
   */
  deltaRatio?: number | undefined
  /** What an increase means for this metric; defaults to neutral. */
  deltaSemantics?: DeltaSemantics | undefined
  /** Sparkline data points over the displayed window, oldest first. */
  series: number[]
  /** CSS color of the value and the sparkline. */
  color: string
  /** Monitoring state shown beside the value; omit to show none. */
  state?: KpiState | undefined
  /**
   * Labels for the ends of the displayed value range, drawn over the sparkline.
   * Omit to leave the range implicit.
   */
  rangeLimits?: KpiRangeLimits | undefined
  /** Turns the value into a link; omit to render it as plain text. */
  href?: string | undefined
}
