/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import {
  ErrorResponse,
  Response,
  type Section,
  type Suggestion,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, ref } from 'vue'

import { ATTRIBUTE_KIND_ORDER, KEY_IDENTS } from './attributeFilterAdapter'
import type { AttributeKindKey, AutoCompleteContext } from './attributeFilterAdapter'

/**
 * Attribute-key autocomplete across the three attribute kinds, sectioned by kind.
 *
 * The caller supplies the REST context, which is what narrows the offered keys.
 * ``buildContext`` receives the id of the pill being edited so it can drop that
 * pill: a condition must not constrain the keys offered for its own key field.
 */
export function useAttributeKeySuggestions(
  buildContext: (excludeId?: string) => AutoCompleteContext
): {
  querySuggestions: (query: string, excludeId?: string) => Promise<Response>
  resolveKind: (key: string) => AttributeKindKey | null
  cachedSuggestions: (
    autocompleter: Autocompleter,
    query: string
  ) => Response | ErrorResponse | undefined
  suggestionRevision: Ref<number>
  clearCache: () => void
} {
  const { _t } = usei18n()

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

  const sectionTitles: Record<AttributeKindKey, TranslatedString> = {
    resource: _t('Resource'),
    scope: _t('Scope'),
    data_point: _t('Data point')
  }

  // A key may be offered under more than one attribute kind, so record the set of
  // kinds each suggested key belongs to (see `resolveKind`).
  const keyKindCache = new Map<string, Set<AttributeKindKey>>()

  function cacheKeyKind(name: string, attributeKind: AttributeKindKey): void {
    const kinds = keyKindCache.get(name)
    if (kinds) {
      kinds.add(attributeKind)
    } else {
      keyKindCache.set(name, new Set([attributeKind]))
    }
  }

  async function querySuggestions(query: string, excludeId?: string): Promise<Response> {
    const sections: Section[] = []
    ATTRIBUTE_KIND_ORDER.forEach((attributeKind) => {
      const autocompleter: Autocompleter = {
        fetch_method: 'rest_autocomplete',
        data: { ident: KEY_IDENTS[attributeKind], params: { context: buildContext(excludeId) } }
      }
      const response = cachedSuggestions(autocompleter, query)
      if (!response || response instanceof ErrorResponse) {
        return
      }
      // The backend echoes the typed text as a leading (query, query) choice; a real
      // key equal to the query is indistinguishable from the echo and is dropped too,
      // falling into the section-less user entry below (its type stays unresolved).
      const suggestions = flattenSuggestions(response.choices).filter(
        (s: Suggestion) =>
          s.name !== query && (s.name === null || (s.name.length > 0 && s.title.length > 0))
      )
      for (const suggestion of suggestions) {
        if (suggestion.name) {
          cacheKeyKind(suggestion.name, attributeKind)
        }
      }
      if (suggestions.length > 0) {
        sections.push({ title: sectionTitles[attributeKind], suggestions })
      }
    })
    const userEntry: Section[] = query
      ? [{ title: untranslated(''), suggestions: [{ name: query, title: untranslated(query) }] }]
      : []
    return new Response([...userEntry, ...sections])
  }

  function resolveKind(key: string): AttributeKindKey | null {
    // A key offered under more than one attribute kind is ambiguous: leave it
    // unresolved so the attribute-kind dropdown opens for the user to choose.
    const kinds = keyKindCache.get(key)
    return kinds?.size === 1 ? [...kinds][0]! : null
  }

  return { querySuggestions, resolveKind, cachedSuggestions, suggestionRevision, clearCache }
}
