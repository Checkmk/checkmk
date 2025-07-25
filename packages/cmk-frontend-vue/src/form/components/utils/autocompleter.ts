/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ErrorResponse, Response } from '@/components/suggestions'
import { fetchSuggestions as fetchSuggestionsViaAjax } from './autocompleters/ajax'
import { fetchSuggestions as fetchSuggestionsViaRest } from './autocompleters/rest'

export async function fetchSuggestions(
  autocompleter: Autocompleter,
  query: string
): Promise<Response | ErrorResponse> {
  if (autocompleter.fetch_method === 'ajax_vs_autocomplete') {
    return fetchSuggestionsViaAjax(autocompleter, query)
  } else if (autocompleter.fetch_method === 'rest_autocomplete') {
    return fetchSuggestionsViaRest(autocompleter, query)
  } else {
    throw new Error(`Internal: Can not fetch data for autocompleter ${autocompleter.fetch_method}`)
  }
}
