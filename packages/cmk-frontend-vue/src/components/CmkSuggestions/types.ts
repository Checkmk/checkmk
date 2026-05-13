/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

import type { ErrorResponse, Response, Suggestion, WarningResponse } from './suggestions'

export type Section = {
  title: TranslatedString
  suggestions: Array<Suggestion>
}

export function isSectioned(input: Array<Suggestion> | Array<Section>): input is Array<Section> {
  const first = input[0]
  return first !== undefined && 'suggestions' in first
}

export function flattenSuggestions(input: Array<Suggestion> | Array<Section>): Array<Suggestion> {
  return isSectioned(input) ? input.flatMap((s) => s.suggestions) : input
}

export type Suggestions = SuggestionsFixed | SuggestionsFiltered | SuggestionsCallbackFiltered

type SuggestionsFixed = {
  type: 'fixed'
  suggestions: Array<Suggestion> | Array<Section>
}

type SuggestionsFiltered = {
  type: 'filtered'
  suggestions: Array<Suggestion> | Array<Section>
}

export type QuerySuggestionsFn = (
  query: string
) => Promise<ErrorResponse | WarningResponse | Response>

type SuggestionsCallbackFiltered = {
  type: 'callback-filtered'
  querySuggestions: QuerySuggestionsFn
}

export class NoSelection {
  getName(): null {
    return null
  }
  getTitle(): null {
    return null
  }
}

export class Selection {
  value: string
  constructor(value: string) {
    this.value = value
  }
  getName(): string {
    return this.value
  }
  getTitle(): null {
    return null
  }
}

export class SelectionWithTitle {
  // we are tightly coupled with CmkDropdown. We have to look up the title
  // there, and want to save one request, so we have to transport the title...
  name: string // id / backend value
  title: string // label / human readable
  constructor(name: string, title: string) {
    this.name = name
    this.title = title
  }
  getName(): string {
    return this.name
  }
  getTitle(): string {
    return this.title
  }
}

export type SuggestionValue = NoSelection | SelectionWithTitle | Selection
