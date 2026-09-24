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

export async function fetchData(
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
        // Every AutocompleterParams field defaults to None and the form spec is
        // serialized with a plain asdict, so the parameters a producer left unset
        // arrive here as null. The autocompleters read them with `.get(key, {})`,
        // which hands back that null instead of the default, so drop them rather
        // than send them. Spread first: AutocompleterParams is an interface, which
        // TypeScript will not assign to the generated open `parameters` record.
        parameters: Object.fromEntries(
          Object.entries({ ...data.params }).filter(([, value]) => value !== null)
        )
      }
    })
  )
}

export async function fetchSuggestions(
  autocompleter: Autocompleter,
  query: string
): Promise<Response | ErrorResponse | WarningResponse> {
  try {
    const result = await fetchData(query, autocompleter.data)
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
