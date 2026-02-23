/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type ComputedRef, type Ref, ref, watch } from 'vue'

import { Response } from '@/components/CmkSuggestions'

import { fetchSuggestions } from '@/form/private/FormAutocompleter/autocompleter'

import type { LabelValueItem } from '@/dashboard/components/Wizard/types'

export function useLabelValueAutocomplete(
  model: Ref<LabelValueItem | null>,
  autocompleter: ComputedRef<Autocompleter>
): { internalValue: Ref<string | null> } {
  const internalValue = ref<string | null>(model.value?.value ?? null)

  watch(model, (val) => {
    const newValue = val?.value ?? null
    if (internalValue.value !== newValue) {
      internalValue.value = newValue
    }
  })

  watch(
    internalValue,
    async (val) => {
      if (val === null) {
        model.value = null
        return
      }
      const result = await fetchSuggestions(autocompleter.value, val)
      if (result instanceof Response) {
        const match = result.choices.find((s) => s.name === val)
        model.value = { value: val, label: match ? (match.title as string) : val }
      } else {
        model.value = { value: val, label: val }
      }
    },
    { immediate: true }
  )

  return { internalValue }
}
