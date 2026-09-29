/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'

type Choices = Array<[string, string]>

export interface AutocompleteRequest {
  ident: string
  value: string
  parameters: Record<string, unknown>
}

/** Answers the REST autocompleters with the `[id, value]` choices `suggest` returns for the request. */
export function restAutocompleter(suggest: (request: AutocompleteRequest) => Choices) {
  return http.post('*/api/internal/objects/autocomplete/*', async ({ request }) => {
    const { value, parameters } = (await request.json()) as Omit<AutocompleteRequest, 'ident'>
    const ident = decodeURIComponent(new URL(request.url).pathname.split('/').pop()!)
    const choices = suggest({ ident, value, parameters })
    return HttpResponse.json({ choices: choices.map(([id, value]) => ({ id, value })) })
  })
}
