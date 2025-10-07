/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cmkFetch } from '@/lib/cmkFetch'
import { CmkError } from '@/lib/error'

export interface MaybeApiError {
  result?: string
  result_code?: number
  severity?: 'error'
}

export class AjaxResponseError extends CmkError {
  response: MaybeApiError

  constructor(message: string, response: MaybeApiError) {
    super(message, null)
    this.response = response
  }

  override getContext(): string {
    if (this.response.result_code !== 0 && this.response.result && this.response.severity) {
      return `${this.response.severity}: ${this.response.result}`
    }
    return ''
  }
}

export async function cmkAjax<OutputType>(method: string, body: object): Promise<OutputType> {
  const response = await cmkFetch(method, {
    method: 'POST',
    headers: {
      'Content-type': 'application/x-www-form-urlencoded'
    },
    body: `request=${JSON.stringify(body)}`
  })
  await response.raiseForStatus()
  const ajaxResponse = (await response.json()) as MaybeApiError
  if (ajaxResponse.result_code !== 0) {
    throw new AjaxResponseError('Endpoint returned an error.', ajaxResponse as MaybeApiError)
  }
  return ajaxResponse.result as OutputType
}
