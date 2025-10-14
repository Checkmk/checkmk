/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'
import createClientImpl from 'openapi-fetch'

import { CmkApiError } from '@/lib/error'
import type { MaybeRestApiCrashReport, MaybeRestApiError } from '@/lib/types'

const API_ROOT = 'api/internal'

/**
 * Unwraps a client response, returning data on success or throwing CmkApiError on error.
 *
 * @example
 * const data = unwrap(await client.GET('/endpoint'))
 *
 * @param result - The result from from the client
 * @returns The data object from a successful response
 * @throws CmkApiError if the response is not 2xx
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined) {
    const context: Array<string> = []
    let message = 'Error in fetch response'

    context.push(
      `${result.response.url}\nSTATUS ${result.response.status}: ${result.response.statusText}`
    )

    // result.error is already the parsed JSON (or raw text if not JSON)
    const parsedJson = result.error

    if (parsedJson !== null && typeof parsedJson === 'object') {
      const crashReportUrl = (parsedJson as MaybeRestApiCrashReport).ext?.details?.crash_report_url
        ?.href
      if (crashReportUrl) {
        context.push(`Crash report: ${crashReportUrl}`)
      }

      const detail = (parsedJson as MaybeRestApiError).detail
      const title = (parsedJson as MaybeRestApiError).title
      if (detail && title) {
        message = `${title}: ${detail}`
      }
    } else {
      throw parsedJson
    }

    throw new CmkApiError(message, null, context.join('\n\n'))
  }

  if (result.data === undefined) {
    throw new CmkApiError('No data in fetch response', null, '')
  }

  return result.data
}

/** Get base url by stripping endpoint resource name
 *
 *  `http://localhost/foo/check_mk/index.py` => `http://localhost/foo/check_mk/${API_ROOT}`
 */
function baseUrl(): string {
  return new URL(API_ROOT, document.location.href).href
}

export function createClient({ baseUrl }: { baseUrl: string }) {
  return createClientImpl<paths, 'application/json'>({
    baseUrl,
    credentials: 'include',
    headers: {
      Accept: 'application/json'
    }
  })
}

const client = createClient({ baseUrl: baseUrl() })

export default client
