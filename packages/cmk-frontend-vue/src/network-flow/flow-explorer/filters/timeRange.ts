/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'

/**
 * The units the network_flow_time filter offers, as seconds-per-unit, largest
 * first. These mirror cmk.gui.query_filters.time_filter_options(), which labels
 * them "days ago" / "hours ago" / "min ago" / "sec ago".
 */
export const TIME_RANGE_UNITS_SECONDS = [86400, 3600, 60, 1] as const

export interface TimeRangeValue {
  /** The count, as the filter's `<ident>_from` htmlvar wants it. */
  from: string
  /** The seconds-per-unit multiplier, as the `<ident>_from_range` htmlvar wants it. */
  range: string
}

/**
 * A duration expressed in the largest offered unit that divides it evenly.
 *
 * The filter multiplies the two back together, so every split of a given
 * duration selects the same window - this only decides how it reads. Picking
 * the largest whole unit is what turns a day-long default from "86400 sec ago"
 * into "1 days ago".
 */
export function asTimeRangeValue(seconds: number): TimeRangeValue {
  const unit = TIME_RANGE_UNITS_SECONDS.find((candidate) => seconds % candidate === 0) ?? 1
  return { from: String(seconds / unit), range: String(unit) }
}

export const TIME_FILTER_ID = 'network_flow_time'

/**
 * The default time range as a network_flow_time filter value, so the listing
 * always runs on a definite window and the Time funnel shows which one - rather
 * than silently falling back to the endpoint's own, shorter default.
 */
export function defaultTimeFilter(seconds: number): ConfiguredFilters {
  const { from, range } = asTimeRangeValue(seconds)
  return {
    [TIME_FILTER_ID]: {
      network_flow_time_from: from,
      network_flow_time_from_range: range,
      network_flow_time_until: '',
      network_flow_time_until_range: '1'
    }
  }
}

/**
 * `context` guaranteed to carry a time range.
 *
 * Unlike every other filter, "no time range" is not a state this listing has:
 * clearing the Time funnel means "back to the default window", not "drop the
 * bound and let the endpoint decide".
 */
export function withDefaultTime(context: ConfiguredFilters, seconds: number): ConfiguredFilters {
  return context[TIME_FILTER_ID] === undefined
    ? { ...context, ...defaultTimeFilter(seconds) }
    : context
}

/**
 * `context` without a time range that is merely the default.
 *
 * For sharing and reloading: a URL naming no time range gets the default back
 * (see the page's initial context), so spelling the default out adds four
 * variables that say nothing. Clearing the filters then leaves a bare URL
 * rather than one that looks filtered.
 */
export function withoutDefaultTime(context: ConfiguredFilters, seconds: number): ConfiguredFilters {
  if (!hasNonDefaultTime(context, seconds) && context[TIME_FILTER_ID] !== undefined) {
    const { [TIME_FILTER_ID]: _default, ...rest } = context
    return rest
  }
  return context
}

/** Whether the time range has been moved off the default - i.e. is worth clearing. */
export function hasNonDefaultTime(context: ConfiguredFilters, seconds: number): boolean {
  const current = context[TIME_FILTER_ID]
  if (current === undefined) {
    return false
  }
  const fallback = defaultTimeFilter(seconds)[TIME_FILTER_ID]!
  return Object.entries(fallback).some(([htmlvar, value]) => current[htmlvar] !== value)
}
