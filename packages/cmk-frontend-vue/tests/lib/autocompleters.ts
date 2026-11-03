/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp } from 'cmk-ui-library/vitest.msw'

type Choices = Array<[string, string]>

export interface AutocompleteRequest {
  ident: string
  value: string
  parameters: Record<string, unknown>
}

/** Answers the REST autocompleters with the `[id, value]` choices `suggest` returns for the request. */
export function restAutocompleter(suggest: (request: AutocompleteRequest) => Choices) {
  return restApiHttp.post(
    '/objects/autocomplete/{autocomplete_id}',
    async ({ params, request, response }) => {
      const { value = '', parameters = {} } = await request.json()
      const choices = suggest({ ident: params.autocomplete_id, value, parameters })
      return response(200).json({ choices: choices.map(([id, value]) => ({ id, value })) })
    }
  )
}
