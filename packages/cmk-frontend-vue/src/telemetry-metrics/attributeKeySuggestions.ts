/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  ErrorResponse,
  Response,
  type Suggestion,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { type Ref, ref } from 'vue'

import { ATTRIBUTE_KIND_ORDER, type KeySection, attributeKindLabel } from './attribute-kind'
import { KEY_IDENTS } from './attributeFilterAdapter'
import type { AutoCompleteContext } from './attributeFilterAdapter'

/**
 * Attribute-key autocomplete across the three attribute kinds, sectioned by kind.
 *
 * The caller supplies the REST context that scopes the offered keys.
 */
export function useAttributeKeySuggestions(buildContext: () => AutoCompleteContext): {
  querySuggestions: (query: string) => Promise<Response>
  cachedSuggestions: (
    autocompleter: Autocompleter,
    query: string
  ) => Response | ErrorResponse | undefined
  suggestionRevision: Ref<number>
  clearCache: () => void
} {
  const suggestionCache = new Map<string, Response | ErrorResponse>()
  const inflightSuggestions = new Set<string>()
  const suggestionRevision = ref(0)

  function cachedSuggestions(
    autocompleter: Autocompleter,
    query: string
  ): Response | ErrorResponse | undefined {
    const key = `${JSON.stringify(autocompleter)}\n${query}`
    const cached = suggestionCache.get(key)
    if (cached) {
      return cached
    }
    if (!inflightSuggestions.has(key)) {
      inflightSuggestions.add(key)
      void fetchSuggestions(autocompleter, query).then((response) => {
        suggestionCache.set(key, response)
        inflightSuggestions.delete(key)
        suggestionRevision.value += 1
      })
    }
    return undefined
  }

  function clearCache(): void {
    suggestionCache.clear()
  }

  async function querySuggestions(query: string): Promise<Response> {
    const sections: KeySection[] = []
    ATTRIBUTE_KIND_ORDER.forEach((attributeKind) => {
      const autocompleter: Autocompleter = {
        fetch_method: 'rest_autocomplete',
        data: { ident: KEY_IDENTS[attributeKind], params: { context: buildContext() } }
      }
      const response = cachedSuggestions(autocompleter, query)
      if (!response || response instanceof ErrorResponse) {
        return
      }
      const suggestions = flattenSuggestions(response.choices).filter(
        (s: Suggestion) => s.name === null || (s.name.length > 0 && s.title.length > 0)
      )
      if (suggestions.length > 0) {
        sections.push({
          title: attributeKindLabel(attributeKind),
          suggestions,
          kind: attributeKind
        })
      }
    })
    // Offer free text only when the query is not already a real key, to avoid a duplicate row.
    const isExactKey = sections.some((section) => section.suggestions.some((s) => s.name === query))
    const userEntry: KeySection[] =
      query && !isExactKey
        ? [{ title: untranslated(''), suggestions: [{ name: query, title: untranslated(query) }] }]
        : []
    return new Response([...userEntry, ...sections])
  }

  return {
    querySuggestions,
    cachedSuggestions,
    suggestionRevision,
    clearCache
  }
}
