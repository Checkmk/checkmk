<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useSlots } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'
import type { ButtonVariants } from '@/components/CmkDropdown/CmkDropdownButton.vue'
import { ErrorResponse, Response, type Suggestion } from '@/components/CmkSuggestions'

import { fetchSuggestions } from '@/form/private/FormAutocompleter/autocompleter'

const props = defineProps<{
  id?: string
  placeholder: TranslatedString
  autocompleter?: Autocompleter
  filter?: (element: Suggestion) => boolean
  startOfGroup?: boolean
  size?: number
  label?: string
  width?: ButtonVariants['width']
  hasError?: boolean
  disabled?: boolean
}>()

const model = defineModel<string | null>({ default: null })

async function suggestionCallback(query: string): Promise<ErrorResponse | Response> {
  if (props.autocompleter === undefined) {
    return new ErrorResponse('internal: props.autocompleter undefined')
  }
  const newValue = await fetchSuggestions(props.autocompleter, query)
  if (newValue instanceof ErrorResponse) {
    return newValue
  }

  let result: Array<Suggestion> = newValue.choices.filter(
    (element: Suggestion) =>
      element.name === null || (element.name.length > 0 && element.title.length > 0)
  )

  if (props.filter !== undefined) {
    result = result.filter(props.filter)
  }

  return new Response(result)
}

const slots = useSlots()
</script>

<template>
  <CmkDropdown
    v-model:selected-option="model"
    :options="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
    :input-hint="placeholder"
    :label="untranslated(label || '')"
    :start-of-group="startOfGroup || false"
    :width="width || 'wide'"
    :form-validation="hasError || false"
    :disabled="disabled || false"
  >
    <template v-if="slots['buttons-start']" #buttons-start>
      <slot name="buttons-start"></slot>
    </template>
    <template v-if="slots['buttons-end']" #buttons-end>
      <slot name="buttons-end"></slot>
    </template>
  </CmkDropdown>
</template>
