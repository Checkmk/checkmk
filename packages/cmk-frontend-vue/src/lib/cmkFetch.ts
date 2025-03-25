/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { CmkError } from '@/lib/error.ts'
import type { MaybeRestApiError, MaybeRestApiCrashReport } from '@/lib/types'

type FetchParams = Parameters<typeof fetch>

class CmkFetchError extends CmkError<Error> {
  context: string

  constructor(message: string, cause: Error | null, context: string) {
    super(message, cause)
    this.context = context
  }
  override getContext(): string {
    return this.context
  }
}

export class CmkFetchResponse {
  response: Response
  jsonReturned: null | unknown = null
  status: Response['status']
  requestOptions: FetchParams[1]

  constructor(response: Response, requestOptions: FetchParams[1]) {
    this.response = response
    this.status = response.status
    this.requestOptions = requestOptions
  }

  async raiseForStatus() {
    if (this.response.status >= 200 && this.response.status <= 299) {
      return
    }
    throw await this.getError(null)
  }

  async getError(cause: Error | null): Promise<CmkFetchError> {
    // tries to extract intresting context from a response, and packs this as a CmkError
    const context: Array<string> = []

    context.push(
      `${this.requestOptions?.method || 'get'} ${this.response.url}\n${this.response.status}: ${this.response.statusText}`
    )

    if (this.jsonReturned !== null) {
      const crashReportUrl = (this.jsonReturned as MaybeRestApiCrashReport).ext?.details
        ?.crash_report_url?.href
      if (crashReportUrl) {
        context.push(`Crash report: ${crashReportUrl}`)
      }
      const detail = (this.jsonReturned as MaybeRestApiError).detail
      const title = (this.jsonReturned as MaybeRestApiError).title
      if (detail && title) {
        context.push(`${title}: ${detail}`)
      }
    }

    return new CmkFetchError('Error in fetch response', cause, context.join('\n\n'))
  }

  // we keep the json definition of original fetch
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async json(): Promise<any> {
    try {
      // we want a detailed error message in getError, but can only consume json once.
      this.jsonReturned = await this.response.json()
      return this.jsonReturned
    } catch (e: unknown) {
      // original error has no stack, so you don't know where the error came from.
      throw new CmkError('Could not parse response as JSON', await this.getError(e as Error))
    }
  }
}

export async function cmkFetch(
  url: FetchParams[0],
  options: FetchParams[1]
): Promise<CmkFetchResponse> {
  const response = await fetch(url, options)
  return new CmkFetchResponse(response, options)
}
