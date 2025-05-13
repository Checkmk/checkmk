/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type {
  Autocompleter,
  AutocompleterData
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { cmkFetch } from '@/lib/cmkFetch'
import { CmkError } from '@/lib/error'

import { ErrorResponse, Response } from '@/components/suggestions'

interface MaybeApiError {
  result?: string
  result_code?: number
  severity?: 'error'
}

class AutoCompleterResponseError extends CmkError {
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

export async function fetchData<OutputType>(
  query: string,
  data: AutocompleterData
): Promise<OutputType> {
  const body = structuredClone(data)
  Object.entries(body.params).forEach(([k, v]) => {
    // ajax_vs_autocomplete.py expects unset parameters, not None
    if (v === null) {
      delete body.params[k as keyof typeof body.params]
    }
  })
  const request = `request=${JSON.stringify({ ...body, value: query })}`

  const response = await cmkFetch('ajax_vs_autocomplete.py', {
    method: 'POST',
    headers: {
      'Content-type': 'application/x-www-form-urlencoded'
    },
    body: request
  })
  await response.raiseForStatus()
  const ajaxResponse = (await response.json()) as MaybeApiError
  if (ajaxResponse.result_code !== 0) {
    throw new AutoCompleterResponseError(
      'Autocompleter endpoint returned an error.',
      ajaxResponse as MaybeApiError
    )
  }
  return ajaxResponse.result as OutputType
}

export type AjaxVsAutocompleterResponse = { choices: Array<[string | null, string]> }

export async function fetchSuggestions(
  autocompleter: Autocompleter,
  query: string
): Promise<Response | ErrorResponse> {
  if (autocompleter.fetch_method === 'ajax_vs_autocomplete') {
    try {
      const result = await fetchData<AjaxVsAutocompleterResponse>(query, autocompleter.data)
      return new Response(
        result.choices.map((element) => ({ name: element[0], title: element[1] }))
      )
    } catch (e: unknown) {
      const errorDescription = (e as AutoCompleterResponseError).response?.result
      return new ErrorResponse(errorDescription || 'unknown error')
    }
  } else {
    throw new Error(`Internal: Can not fetch data for autocompleter ${autocompleter.fetch_method}`)
  }
}
