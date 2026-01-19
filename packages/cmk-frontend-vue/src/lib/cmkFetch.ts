/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkError } from '@/lib/error.ts'
import type { MaybeRestApiCrashReport, MaybeRestApiError } from '@/lib/types'

type FetchParams = Parameters<typeof fetch>

export class CmkFetchError extends CmkError<Error> {
  context: string
  statusCode: number

  constructor(message: string, cause: Error | null, context: string, statusCode: number) {
    super(message, cause)
    this.context = context
    this.statusCode = statusCode
  }
  override getContext(): string {
    return this.context
  }

  getStatusCode(): number {
    return this.statusCode
  }
}

export class CmkFetchResponse {
  response: Response
  jsonReturned: null | unknown = null
  status: Response['status']
  requestOptions: FetchParams[1]
  jsonConsumed: boolean = false

  constructor(response: Response, requestOptions: FetchParams[1]) {
    this.response = response
    this.status = response.status
    this.requestOptions = requestOptions
  }

  /**
   * Raise any fatal error.
   *
   * This should end the program flow if the response is not ok, please
   * test for any possibly expected errors before.
   */
  async raiseForStatus() {
    if (this.response.status >= 200 && this.response.status <= 299) {
      return
    }
    throw await this.getError(null)
  }

  async getError(cause: Error | null): Promise<CmkFetchError> {
    // tries to extract interesting context from a response, and packs this as a CmkError
    const context: Array<string> = []

    let message = 'Error in fetch response'

    context.push(
      `${this.requestOptions?.method || 'GET'} ${this.response.url}\nSTATUS ${this.response.status}: ${this.response.statusText}`
    )

    // you normally use raiseForStatus before you consume the json document
    // but then we can not display the detailed error information,
    // so we consume the json here manually to indirectly set this.jsonReturned
    if (!this.jsonConsumed) {
      try {
        await this.json()
      } catch (e: unknown) {
        // we want to ignore the CmkError resulting from this call: maybe the
        // original request did not call json(), and this additional error
        // would be quite confusing.
        if (e instanceof CmkError) {
          console.info('cmkFetch: tried to parse response as json but failed')
        } else {
          throw e
        }
      }
    }

    if (this.jsonReturned !== null) {
      const crashReportUrl = (this.jsonReturned as MaybeRestApiCrashReport).ext?.details
        ?.crash_report_url?.href
      if (crashReportUrl) {
        context.push(`Crash report: ${crashReportUrl}`)
      }
      const detail = (this.jsonReturned as MaybeRestApiError).detail
      const title = (this.jsonReturned as MaybeRestApiError).title
      if (detail && title) {
        message = `${title}: ${detail}`
      }
    }

    return new CmkFetchError(message, cause, context.join('\n\n'), this.status)
  }

  // we keep the json definition of original fetch
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async json(): Promise<any> {
    // technically we set this variable too soon, but otherwise we could land
    // in a infinite recursion via this.getError
    this.jsonConsumed = true
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

export async function fetchRestAPI<Payload>(url: string, method: string, body?: Payload) {
  const params: RequestInit = {
    method,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json'
    }
  }
  if (body) {
    params.body = JSON.stringify(body)
  }
  const response = await cmkFetch(url, params)
  return response
}
