/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'

/** The suggestions plus a stored name none of them offers, labelled by itself. */
export function withStoredName(suggestions: Suggestion[], stored: string | null): Suggestion[] {
  if (stored === null || suggestions.some(({ name }) => name === stored)) {
    return suggestions
  }
  return [...suggestions, { name: stored, title: untranslated(stored) }]
}
