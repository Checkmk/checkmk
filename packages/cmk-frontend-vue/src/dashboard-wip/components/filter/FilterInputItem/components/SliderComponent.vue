<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import type { SliderConfig } from '../../types.ts'
import CmkSlider from './SliderInput.vue'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const props = defineProps<FilterComponentProps<SliderConfig>>()
const emit = defineEmits<ComponentEmits>()

const getInitialValue = (): number => {
  const configuredValue = props.configuredValues?.[props.component.id]
  if (configuredValue !== undefined && configuredValue !== null) {
    return parseInt(configuredValue.toString(), 10)
  }
  return props.component.default_value
}

const currentValue = ref(getInitialValue())

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, {
    [props.component.id]: `${currentValue.value}`
  })
}

watch(currentValue, (newValue) => {
  emit('update-component-values', props.component.id, { [props.component.id]: `${newValue}` })
})

const handleValueUpdate = (value: number): void => {
  currentValue.value = value
}
</script>

<template>
  <CmkSlider
    :model-value="currentValue"
    :min="component.min_value"
    :max="component.max_value"
    :step="component.step"
    @update:model-value="handleValueUpdate"
  />
</template>
