<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'

import { cmkFetch } from '@/lib/cmkFetch.ts'
import usei18n from '@/lib/i18n'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

import type { DynamicDropdownConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const props = defineProps<FilterComponentProps<DynamicDropdownConfig>>()
const emit = defineEmits<ComponentEmits>()

const { _t } = usei18n()
const validationError = ref<string>('')

const getInitialValue = (): string | null => {
  const storedValue = props.configuredValues?.[props.component.id]
  if (storedValue !== undefined && storedValue !== '') {
    return storedValue
  }
  return null
}

const currentValue = ref(getInitialValue())

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, {
    [props.component.id]: currentValue.value ?? ''
  })
}

const validateValue = async (value: string | null): Promise<void> => {
  if (!props.component.has_validation || !value) {
    validationError.value = ''
    return
  }

  const response = await cmkFetch('ajax_validate_filter.py', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      filter_id: props.component.id,
      value: value
    })
  })

  await response.raiseForStatus()

  const data = await response.json()
  validationError.value = data.result?.error_html || ''
}

watch(currentValue, async (newValue) => {
  emit('update-component-values', props.component.id, { [props.component.id]: newValue ?? '' })
  await validateValue(newValue)
})

const autocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: props.component.autocompleter
}
</script>

<template>
  <div>
    <FormAutocompleter
      v-model="currentValue"
      :autocompleter="autocompleter"
      :size="0"
      :width="'fill'"
      :placeholder="_t('Type to search...')"
    />

    <!-- eslint-disable vue/no-v-html -->
    <div v-if="validationError" class="error" v-html="validationError"></div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.error {
  color: #dc2626;
  margin-top: 4px;
  font-size: 14px;
}
</style>
