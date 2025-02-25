/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import type {
  Autocompleter,
  AutocompleterData
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { cmkFetch } from '@/lib/cmkFetch'
import { CmkError } from '@/lib/error'

interface MaybeApiError {
  result?: string
  result_code?: number
  severity?: 'error'
}

class AutoCompleterResponseError extends CmkError<null> {
  response: MaybeApiError

  constructor(message: string, response: MaybeApiError) {
    super(message, null)
    this.response = response
  }

  override getContext(): string {
    if (this.response.result_code !== 0 && this.response.result && this.response.severity) {
      return `${this.response.severity}: ${this.response.result}`
    }
    return ''
  }
}

export async function fetchData<OutputType>(
  value: unknown,
  data: AutocompleterData
): Promise<OutputType> {
  const body = structuredClone(data)
  Object.entries(body.params).forEach(([k, v]) => {
    // ajax_vs_autocomplete.py expects unset parameters, not None
    if (v === null) {
      delete body.params[k as keyof typeof body.params]
    }
  })
  const request = `request=${JSON.stringify({ ...body, value })}`

  const response = await cmkFetch('ajax_vs_autocomplete.py', {
    method: 'POST',
    headers: {
      'Content-type': 'application/x-www-form-urlencoded'
    },
    body: request
  })
  await response.raiseForStatus()
  const ajaxResponse = (await response.json()) as MaybeApiError
  if (ajaxResponse.result_code !== 0) {
    throw new AutoCompleterResponseError(
      'Autocompleter endpoint returned an error.',
      ajaxResponse as MaybeApiError
    )
  }
  return ajaxResponse.result as OutputType
}

export function setupAutocompleter<OutputType>(getAutocompleter: () => Autocompleter | null): {
  input: Ref<string | undefined>
  output: Ref<OutputType | undefined>
  error: Ref<string>
} {
  const input = ref<string>()
  const output = ref<OutputType>()
  const error = ref<string>('')

  watch([input, getAutocompleter], async ([_, autocompleter]) => {
    if (autocompleter === null) {
      return
    }
    if (autocompleter.fetch_method === 'ajax_vs_autocomplete') {
      error.value = ''
      try {
        output.value = await fetchData<OutputType>(input.value, autocompleter.data)
      } catch (e: unknown) {
        const errorDescription = (e as AutoCompleterResponseError).response?.result
        console.log('error!', errorDescription)
        error.value = errorDescription || ''
        output.value = undefined
      }
    }
  })

  return { input, output, error }
}
