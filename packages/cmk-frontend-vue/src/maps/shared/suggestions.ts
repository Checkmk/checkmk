/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Response, type Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { type Ref, computed } from 'vue'

/**
 * A host list from a large site runs into the thousands, and every entry of a
 * ``filtered`` dropdown is rendered as soon as it opens. Matching is therefore
 * done here and only this many results are handed on; the operator narrows the
 * rest by typing.
 */
const SUGGESTION_LIMIT = 500

/** Names as they come from the daemon, which has no titles to offer. */
export function namedSuggestions(names: readonly string[]): Suggestion[] {
  return names.map((name) => ({ name, title: untranslated(name) }))
}

/** Ids with a human title beside them (maps, BI aggregations, metrics). */
export function titledSuggestions(entries: readonly { id: string; title: string }[]): Suggestion[] {
  return entries.map(({ id, title }) => ({ name: id, title: untranslated(title || id) }))
}

/**
 * Serve an already-fetched list to a ``callback-filtered`` CmkDropdown.
 *
 * The list is a plain array the caller owns, so matching costs nothing and
 * needs no round-trip — the callback shape is what buys the cap above and lets
 * a value the list no longer carries still resolve to its own label.
 *
 * The id is matched beside the title because this callback is also how the
 * dropdown resolves the label of the value it already holds: it passes that
 * value through as the query. A list whose ids differ from its titles (maps,
 * BI aggregations, metrics) would otherwise answer "nothing matches" for its
 * own value, and the field would read as empty over a binding that is set.
 */
export function localSuggestions(
  suggestions: () => Suggestion[]
): (query: string) => Promise<Response> {
  return (query: string) => {
    const needle = query.trim().toLowerCase()
    const all = suggestions()
    const matching = needle
      ? all.filter(
          (suggestion) =>
            suggestion.title.toLowerCase().includes(needle) ||
            !!suggestion.name?.toLowerCase().includes(needle)
        )
      : all
    return Promise.resolve(new Response(matching.slice(0, SUGGESTION_LIMIT)))
  }
}

/**
 * What a picker needs to know about the list behind it: the entries, and
 * whether they are still on their way — a list not yet loaded must not read as
 * an empty one.
 */
export interface SuggestionList {
  items: Readonly<Ref<Suggestion[]>>
  loading: Readonly<Ref<boolean>>
}

/** Turns a caller's own reactive source into the shape a picker takes. */
export function suggestionList(
  items: () => Suggestion[],
  loading: () => boolean = () => false
): SuggestionList {
  return { items: computed(items), loading: computed(loading) }
}
