/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { RequestedTimeRange } from '@/graphing/types'
import type { ServiceNameMatch } from '@/mode-alerts/types'

export type Preview = components['schemas']['AlertPreviewModel']

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
      await client.POST('/domain-types/telemetry_alert/actions/preview_data/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          service_match: { mode: match, pattern },
          requested_time_range: requestedTimeRange
        }
      })
    )
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode === 422) {
      return {
        time_range: requestedTimeRange,
        metrics: [],
        horizontal_lines: [],
        service_units: [],
        notice: problemDetail(error),
        warnings: [],
        errors: []
      }
    }
    throw error
  }
}
