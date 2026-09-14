/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type {
  Autocompleter,
  AutocompleterData
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ErrorResponse, Response, WarningResponse } from 'cmk-ui-library/components/CmkSuggestions'
import type { CmkError } from 'cmk-ui-library/lib/error'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export type RestAutocompleterResponse = components['schemas']['AutocompleteResponseModel']

export async function fetchtData(
  value: string,
  data: AutocompleterData
): Promise<RestAutocompleterResponse> {
  return unwrap(
    await client.POST('/objects/autocomplete/{autocomplete_id}', {
      params: {
        header: { 'Content-Type': 'application/json' },
        path: { autocomplete_id: data.ident }
      },
      body: {
        value,
        // spread: AutocompleterParams is an interface, which TypeScript will not
        // assign to the generated open `parameters` record
        parameters: { ...data.params }
      }
    })
  )
}

export async function fetchSuggestions(
  autocompleter: Autocompleter,
  query: string
): Promise<Response | ErrorResponse | WarningResponse> {
  if (autocompleter.fetch_method !== 'rest_autocomplete') {
    throw new Error(`Internal: Can not fetch data for autocompleter ${autocompleter.fetch_method}`)
  }

  try {
    const result = await fetchtData(query, autocompleter.data)
    const choices = result.choices.map((element) => ({
      name: element.id,
      title: untranslated(element.value)
    }))

    if (result.warning) {
      return new WarningResponse(result.warning, choices)
    }

    return new Response(choices)
  } catch (e: unknown) {
    const errorDescription = (e as CmkError)?.message || 'unknown error'
    return new ErrorResponse(errorDescription)
  }
}
