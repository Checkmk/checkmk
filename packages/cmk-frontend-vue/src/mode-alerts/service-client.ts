/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { AlertConditions, ServiceNameMatch } from '@/mode-alerts/types'

export type ServiceSearchResult = components['schemas']['ServiceSearchResultModel']
export type FoundService = components['schemas']['FoundServiceModel']
export type UnitSummary = components['schemas']['UnitSummaryModel']

// The server caps the list and the names at this many.
export const MAX_SERVICES = 200

/**
 * The custom services the service match selects on the hosts the conditions select, including
 * services not discovered yet. Throws CmkApiError on HTTP error.
 */
export async function searchServices(
  match: ServiceNameMatch,
  pattern: string,
  conditions?: AlertConditions
): Promise<ServiceSearchResult> {
  return unwrap(
    await client.POST('/domain-types/telemetry_alert/actions/search_services/invoke', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: {
        service_match: { mode: match, pattern },
        ...(conditions === undefined ? {} : { conditions })
      }
    })
  )
}

/**
 * Why the server refused the service pattern, or `null` if the error is about something else.
 * The server decides, in the regular expression dialect of the alert's rule.
 */
export function patternErrorOf(error: unknown): string | null {
  if (!(error instanceof CmkApiError) || error.statusCode !== 400) {
    return null
  }
  const fields = (error.body as { fields?: unknown } | null | undefined)?.fields
  if (typeof fields !== 'object' || fields === null) {
    return null
  }
  for (const field of Object.values(fields)) {
    const { loc, msg } = field as { loc?: unknown; msg?: unknown }
    if (Array.isArray(loc) && loc.at(-1) === 'pattern' && typeof msg === 'string') {
      return msg.replace(/^Value error,\s*/, '')
    }
  }
  return null
}

function asLiteral(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * A pattern finding the names that contain what was typed so far, so a partially typed name
 * still has suggestions.
 */
export function suggestionPattern(match: ServiceNameMatch, typed: string): string {
  return match === 'exact' ? `.*${asLiteral(typed)}` : `.*(?:${typed})`
}
