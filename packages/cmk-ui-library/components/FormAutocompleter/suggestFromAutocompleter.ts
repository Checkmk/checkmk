/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  ErrorResponse,
  Response,
  type Suggestion,
  WarningResponse,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'

/** The suggestions of an autocompleter for a query that pass the filter, without empty entries. */
export async function suggestFromAutocompleter(
  autocompleter: Autocompleter,
  query: string,
  filter?: (suggestion: Suggestion) => boolean
): Promise<ErrorResponse | WarningResponse | Response> {
  const response = await fetchSuggestions(autocompleter, query)
  if (response instanceof ErrorResponse || response instanceof WarningResponse) {
    return response
  }
  return new Response(
    flattenSuggestions(response.choices).filter(
      (suggestion) =>
        (suggestion.name === null || (suggestion.name.length > 0 && suggestion.title.length > 0)) &&
        (filter === undefined || filter(suggestion))
    )
  )
}
