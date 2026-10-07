/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

import type { FilterHTTPVars, VisualContext } from '@/dashboard/types/widget'

export interface IFrameUrlParameters {
  /** `null` leaves the filters out. */
  context: VisualContext | null
  /** `null` leaves the time range out. */
  timeRange: DateTimeRange | null
}

function isSet(variable: string, value: string): boolean {
  return variable.startsWith('is_') ? value !== '-1' : value !== ''
}

function setFilters(context: VisualContext): FilterHTTPVars[] {
  return Object.values(context).filter((variables) =>
    Object.entries(variables).some(([variable, value]) => isSet(variable, value))
  )
}

function timeRangeVariables(range: DateTimeRange): FilterHTTPVars {
  return {
    from: String(range.from.toDate().getTime()),
    to: String(range.to.toDate().getTime())
  }
}

/** The URL of an iframe widget, with the dashboard parameters it includes. */
export function iframeUrl(url: string, parameters: IFrameUrlParameters): string {
  const variables = [
    ...(parameters.context === null ? [] : setFilters(parameters.context)),
    ...(parameters.timeRange === null ? [] : [timeRangeVariables(parameters.timeRange)])
  ]
  if (variables.length === 0) {
    return url
  }

  const [withoutFragment, fragment] = splitOnce(url, '#')
  const [path, query] = splitOnce(withoutFragment, '?')
  const params = new URLSearchParams(query ?? '')
  for (const group of variables) {
    for (const [variable, value] of Object.entries(group)) {
      params.set(variable, value)
    }
  }
  return `${path}?${params.toString()}${fragment === undefined ? '' : `#${fragment}`}`
}

function splitOnce(value: string, separator: string): [string, string | undefined] {
  const index = value.indexOf(separator)
  return index === -1 ? [value, undefined] : [value.slice(0, index), value.slice(index + 1)]
}
