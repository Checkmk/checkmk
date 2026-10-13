/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { Response, flattenSuggestions } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import { type ComputedRef, type Ref, ref, watch } from 'vue'

import type { LabelValueItem } from '@/dashboard/components/Wizard/types'

export function useLabelValueAutocomplete(
  model: Ref<LabelValueItem | null>,
  autocompleter: ComputedRef<Autocompleter>
): { internalValue: Ref<string | null>; pending: Ref<boolean> } {
  const internalValue = ref<string | null>(model.value?.value ?? null)
  const pending = ref<boolean>(false)
  let latestSelectionId = 0

  watch(model, (val) => {
    const newValue = val?.value ?? null
    if (internalValue.value !== newValue) {
      internalValue.value = newValue
    }
  })

  watch(
    internalValue,
    async (val) => {
      const selectionId = ++latestSelectionId

      if (val === null) {
        model.value = null
        pending.value = false
        return
      }

      // Commit before awaiting, so a synchronous validate() cannot see a null model.
      model.value = { value: val, label: val }

      pending.value = true
      try {
        const result = await fetchSuggestions(autocompleter.value, val)
        // A newer selection has superseded this response.
        if (selectionId !== latestSelectionId) {
          return
        }
        if (result instanceof Response) {
          const match = flattenSuggestions(result.choices).find((s) => s.name === val)
          if (match) {
            model.value = { value: val, label: match.title as string }
          }
        }
      } finally {
        if (selectionId === latestSelectionId) {
          pending.value = false
        }
      }
    },
    { immediate: true }
  )

  return { internalValue, pending }
}
