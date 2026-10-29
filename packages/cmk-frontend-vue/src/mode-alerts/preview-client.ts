/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { networkAwareFetch } from 'cmk-ui-library/lib/networkAwareFetch'
import { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import createClient from 'openapi-fetch'

import type { HorizontalLine, Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph'
import type { RequestedTimeRange } from '@/graphing/types'
import type { ServiceNameMatch } from '@/mode-alerts/types'

const PREVIEW_PATH = '/domain-types/telemetry_alert/actions/preview_data/invoke'

interface PreviewRequest {
  service_name_match: ServiceNameMatch
  service_name_pattern: string
  requested_time_range: TimeRange
  consolidation_function: 'min' | 'max' | 'avg'
}

export interface Preview {
  time_range: TimeRange
  metrics: Metric[]
  horizontal_lines: HorizontalLine[]
  notice: string | null
  warnings: string[]
  errors: string[]
}

// TODO(CMK-40260): drop these and use the shared client once the endpoint is in the spec.
interface PreviewPaths {
  [PREVIEW_PATH]: {
    post: {
      requestBody: { content: { 'application/json': PreviewRequest } }
      responses: { 200: { content: { 'application/json': Preview } } }
    }
  }
}

const previewClient = createClient<PreviewPaths, 'application/json'>({
  baseUrl: new URL('api/internal', document.location.href).href,
  credentials: 'include',
  headers: { Accept: 'application/json' },
  fetch: networkAwareFetch
})

function problemDetail(error: CmkApiError): string {
  const body = error.body
  if (body !== null && typeof body === 'object' && 'detail' in body) {
    return String(body.detail)
  }
  return error.message
}

export async function fetchPreview(
  match: ServiceNameMatch,
  pattern: string,
  range: RequestedTimeRange,
  step: number
): Promise<Preview> {
  const requestedTimeRange = { start: range.start, end: range.end, step }
  try {
    return unwrap(
      await previewClient.POST(PREVIEW_PATH, {
        body: {
          service_name_match: match,
          service_name_pattern: pattern,
          requested_time_range: requestedTimeRange,
          consolidation_function: 'max'
        }
      })
    )
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode === 422) {
      return {
        time_range: requestedTimeRange,
        metrics: [],
        horizontal_lines: [],
        notice: problemDetail(error),
        warnings: [],
        errors: []
      }
    }
    throw error
  }
}
