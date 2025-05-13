<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from '@/components/CmkDropdown.vue'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Suggestion, ErrorResponse, Response } from '@/components/suggestions'
import { fetchSuggestions } from '@/form/components/utils/autocompleter'

const props = defineProps<{
  id?: string
  placeholder: string
  autocompleter?: Autocompleter
  filter?: (element: Suggestion) => boolean
  startOfGroup?: boolean
  size: number
  label?: string
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
</script>

<template>
  <CmkDropdown
    v-model:selected-option="model"
    :options="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
    :input-hint="placeholder"
    :label="label || ''"
    :start-of-group="startOfGroup || false"
    width="wide"
  />
</template>
