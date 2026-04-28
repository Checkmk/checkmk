/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ErrorResponse, Response, Suggestion, WarningResponse } from './suggestions'

export type Suggestions = SuggestionsFixed | SuggestionsFiltered | SuggestionsCallbackFiltered

type SuggestionsFixed = {
  type: 'fixed'
  suggestions: Array<Suggestion>
}

type SuggestionsFiltered = {
  type: 'filtered'
  suggestions: Array<Suggestion>
}

type SuggestionsCallbackFiltered = {
  type: 'callback-filtered'
  querySuggestions: (query: string) => Promise<ErrorResponse | WarningResponse | Response>
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
