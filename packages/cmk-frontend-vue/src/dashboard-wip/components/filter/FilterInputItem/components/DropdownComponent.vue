<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import type { Suggestions } from '@/components/CmkSuggestions.vue'

import type { DropdownConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const { _t } = usei18n()

const props = defineProps<FilterComponentProps<DropdownConfig>>()
const emit = defineEmits<ComponentEmits>()

const getInitialValue = (): string => {
  const storedValue = props.configuredValues?.[props.component.id]
  if (storedValue !== undefined) {
    return storedValue
  }
  return props.component.default_value !== undefined ? props.component.default_value : ''
}

const currentValue = ref(getInitialValue())

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, { [props.component.id]: currentValue.value })
}

watch(currentValue, (newValue) => {
  emit('update-component-values', props.component.id, { [props.component.id]: newValue })
})

const dropdownOptions = computed((): Suggestions => {
  const suggestions = Object.entries(props.component.choices).map(([value, label]) => ({
    name: value,
    title: untranslated(label || (value === '' ? '(empty)' : value))
  }))

  return {
    type: 'fixed',
    suggestions
  }
})

const handleValueUpdate = (value: string | null): void => {
  if (value === null) {
    currentValue.value =
      props.component.default_value !== undefined ? props.component.default_value : ''
  } else {
    currentValue.value = value
  }
}
</script>

<template>
  <CmkDropdown
    :selected-option="currentValue"
    :options="dropdownOptions"
    :label="untranslated(component.label ?? '')"
    :input-hint="_t('Select an option...')"
    :no-results-hint="_t('No options available')"
    @update:selected-option="handleValueUpdate"
  />
</template>
