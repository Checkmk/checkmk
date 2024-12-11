/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import type { Autocompleter } from '@/form/components/vue_formspec_components'
import { cmkFetch } from '@/lib/cmkFetch'

interface AjaxResponse {
  result: unknown
  result_code: number
  severity: string
}

export async function fetchData<OutputType>(
  value: unknown,
  data: Record<string, unknown>
): Promise<OutputType> {
  const body = JSON.parse(JSON.stringify(data)) as Record<string, unknown>
  body['value'] = value
  const request = `request=${JSON.stringify(body)}`

  const response = await cmkFetch('ajax_vs_autocomplete.py', {
    method: 'POST',
    headers: {
      'Content-type': 'application/x-www-form-urlencoded'
    },
    body: request
  })
  await response.raiseForStatus()
  const ajaxResponse = (await response.json()) as AjaxResponse
  if (ajaxResponse.result_code !== 0) {
    throw new Error(`AjaxResponse error! result code: ${ajaxResponse.result_code}`)
  }
  return ajaxResponse.result as OutputType
}

export function setupAutocompleter<OutputType>(autocompleter: Autocompleter | null): {
  input: Ref<string>
  focus: Ref<boolean>
  output: Ref<OutputType | undefined>
} {
  const input = ref<string>('')
  const output = ref<OutputType>()
  const focus = ref(false)
  if (autocompleter === null) {
    return { input, focus, output }
  }
  watch(input, async () => {
    await updateOutput()
  })

  watch(focus, async () => {
    if (focus.value) {
      await updateOutput()
    }
  })

  const updateOutput = async () => {
    if (autocompleter.fetch_method === 'ajax_vs_autocomplete') {
      await fetchData<OutputType>(input.value, autocompleter.data).then((result: OutputType) => {
        output.value = result
      })
    }
  }

  return { input, focus, output }
}
