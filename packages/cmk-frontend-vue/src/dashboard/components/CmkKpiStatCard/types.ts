/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
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

/** 'band' keeps the sparkline strictly below the numbers; 'full' runs it behind them, behind a scrim. */
export type SparkHeightMode = 'band' | 'full'

/** What the current value is compared against, computed over real samples in the displayed window. */
export type ComparisonBasis = 'average' | 'last' | 'minimum' | 'maximum' | 'median'

/**
 * A ready-made delta, computed by the caller instead of derived from `series`.
 * For callers whose headline `value` is a window aggregate (a sum, or a
 * deduplicated count) rather than `series`'s own last sample - comparing two
 * per-bucket samples out of `series` would be meaningless there, since neither
 * is on the same scale as the aggregate headline.
 */
export interface KpiDelta {
  /** Absolute percentage, formatted, e.g. "5.7%". */
  percent: string
  /** True if the value increased; flips the triangle direction when false. */
  up: boolean
  /** Full comparison text shown beside the percent, e.g. "vs. 21.0k prev. window". */
  comparisonText: string
}

/** Configures the delta indicator - what it compares against and whether it shows at all. */
export interface KpiDeltaConfig {
  /** Hides the delta indicator entirely, regardless of the data; defaults to true. */
  show?: boolean | undefined
  /**
   * What the delta compares the current value against; defaults to 'average'.
   * Delta is hidden entirely when fewer than two real samples exist. Ignored
   * when `override` is given.
   */
  comparisonBasis?: ComparisonBasis | undefined
  /**
   * A ready-made delta, taking priority over `comparisonBasis`/`series`. For
   * callers whose `value` is a window aggregate rather than a live reading -
   * see `KpiDelta`.
   */
  override?: KpiDelta | undefined
  /**
   * True when the caller computes its own delta via `override`, so an
   * undefined value this render stays empty instead of falling back to the
   * wrong series-derived one.
   */
  fromCaller?: boolean | undefined
}

/**
 * Fixed vertical scale bounds for the sparkline, as raw numbers (unrelated to
 * KpiRangeLimits, which is display-only formatted labels). Samples outside
 * this range clamp to the edge and are marked with a tick.
 */
export interface KpiValueRange {
  minimum: number
  maximum: number
}

/**
 * A single sparkline sample. `value` is null for a bucket with no data - an
 * explicit gap, not a zero reading.
 */
export interface TimestampedSample {
  /** Unix epoch seconds. */
  timestamp: number
  value: number | null
}

export interface CmkKpiStatCardProps {
  /**
   * The widget's own title, read as part of the composite aria-label on focus
   * (accessibility only - rendered elsewhere).
   */
  title?: string | undefined
  /** Pre-formatted headline value, e.g. "801.84" or "4.3". Omit for "no data". */
  value?: string | undefined
  /** Unit rendered after the value, e.g. "GB" or "K"; omit for plain counts. */
  unit?: string | undefined
  /** Sparkline data points over the displayed window, oldest first; omit for a plain value. */
  series?: TimestampedSample[] | undefined
  /** Configures the delta indicator; omit for the defaults (shown, averaged over `series`). */
  delta?: KpiDeltaConfig | undefined
  /**
   * Formats a raw sample value the same way `value` was formatted, for the
   * comparison basis text. Defaults to a plain one-decimal number for
   * consumers with no formatter of their own.
   */
  formatValue?: ((value: number) => string) | undefined
  /** CSS color of the value and the sparkline. */
  color: string
  /** Monitoring state shown beside the value; omit to show none. */
  state?: KpiState | undefined
  /**
   * Overrides the "No recent data" staleness indicator instead of deriving it
   * from whether `series` ends in a trailing gap. For callers whose value isn't
   * backed by a series at all (e.g. a current-value-only reading), where a
   * caller-known staleness signal (e.g. the check's own staleness) is the only
   * one available.
   */
  stale?: boolean | undefined
  /**
   * Labels for the ends of the displayed value range, drawn over the sparkline.
   * Omit to leave the range implicit.
   */
  rangeLimits?: KpiRangeLimits | undefined
  /**
   * Fixed vertical scale bounds for the sparkline. Omit for the default:
   * automatic, padded to the data.
   */
  range?: KpiValueRange | undefined
  /** Turns the value into a link; omit to render it as plain text. */
  href?: string | undefined
  /** How much of the card the sparkline occupies; defaults to 'full'. */
  sparkHeightMode?: SparkHeightMode | undefined
}
