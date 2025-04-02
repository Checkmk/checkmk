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
  filterOn: string[]
  startOfGroup?: boolean
  size: number
  resetInputOnAdd: boolean
  label?: string
}>()

const model = defineModel<string>({ default: '' })

async function suggestionCallback(query: string): Promise<ErrorResponse | Response> {
  if (props.autocompleter === undefined) {
    return new ErrorResponse('internal: props.autocompleter undefined')
  }
  const newValue = await fetchSuggestions(props.autocompleter, query)
  if (newValue instanceof ErrorResponse) {
    return newValue
  }

  const result: Array<Suggestion> = []

  result.push(
    ...newValue.choices
      .filter((element: Suggestion) => element.name.length > 0 && element.title.length > 0)
      .filter((element: Suggestion) => !props.filterOn.includes(element.name))
  )

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
