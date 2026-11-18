<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { ButtonVariants } from 'cmk-ui-library/components/CmkDropdown/CmkDropdownButton.vue'
import {
  ErrorResponse,
  type Response,
  type Suggestion,
  type WarningResponse
} from 'cmk-ui-library/components/CmkSuggestions'
import { suggestFromAutocompleter } from 'cmk-ui-library/components/FormAutocompleter/suggestFromAutocompleter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useSlots } from 'vue'

const { _t } = usei18n()

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
  describedBy?: string | undefined
  disabled?: boolean
  floating?: boolean
  busy?: boolean
}>()

const model = defineModel<string | null>({ default: null })

async function suggestionCallback(
  query: string
): Promise<ErrorResponse | WarningResponse | Response> {
  if (props.autocompleter === undefined) {
    return new ErrorResponse('internal: props.autocompleter undefined')
  }
  return suggestFromAutocompleter(props.autocompleter, query, props.filter)
}

const slots = useSlots()
</script>

<template>
  <CmkDropdown
    v-model="model"
    :component-id="id ?? null"
    :options="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
    :input-hint="placeholder"
    :label="untranslated(label || '')"
    :start-of-group="startOfGroup || false"
    :width="width || 'wide'"
    :no-results-hint="_t('No results found')"
    :form-validation="hasError || false"
    :described-by="describedBy"
    :disabled="disabled || false"
    :floating="floating || false"
    :busy="busy || false"
  >
    <template v-if="slots['buttons-start']" #buttons-start>
      <slot name="buttons-start"></slot>
    </template>
    <template v-if="slots['buttons-end']" #buttons-end>
      <slot name="buttons-end"></slot>
    </template>
  </CmkDropdown>
</template>
