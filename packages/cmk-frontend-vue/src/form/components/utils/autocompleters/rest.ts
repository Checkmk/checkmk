/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  Autocompleter,
  AutocompleterData
} from 'cmk-shared-typing/typescript/vue_formspec_components'

import { fetchRestAPI } from '@/lib/cmkFetch'
import type { CmkError } from '@/lib/error'
import { API_ROOT } from '@/lib/rest-api-client/constants'

import { ErrorResponse, Response } from '@/components/suggestions'

const AUTOCOMPLETER_API = `${API_ROOT}/objects/autocomplete/{autocompleter}`

type RestAutocompleterChoice = {
  id: string | null
  value: string
}
export type RestAutocompleterResponse = { choices: RestAutocompleterChoice[] }

export async function fetchtData(
  value: string,
  data: AutocompleterData
): Promise<RestAutocompleterChoice[]> {
  const payload = {
    value,
    parameters: data.params
  }

  const url = AUTOCOMPLETER_API.replace('{autocompleter}', data.ident)

  const response = await fetchRestAPI(url, 'POST', payload)

  await response.raiseForStatus()
  const ajaxResponse = (await response.json()) as RestAutocompleterResponse

  return ajaxResponse.choices as RestAutocompleterChoice[]
}

export async function fetchSuggestions(
  autocompleter: Autocompleter,
  query: string
): Promise<Response | ErrorResponse> {
  if (autocompleter.fetch_method !== 'rest_autocomplete') {
    throw new Error(`Internal: Can not fetch data for autocompleter ${autocompleter.fetch_method}`)
  }

  try {
    const result = await fetchtData(query, autocompleter.data)
    return new Response(result.map((element) => ({ name: element.id, title: element.value })))
  } catch (e: unknown) {
    const errorDescription = (e as CmkError)?.message || 'unknown error'
    return new ErrorResponse(errorDescription)
  }
}
