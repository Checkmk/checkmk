<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import type { RadioButtonConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const props = defineProps<FilterComponentProps<RadioButtonConfig>>()
const emit = defineEmits<ComponentEmits>()

const getInitialValue = (): string => {
  return props.configuredValues?.[props.component.id] ?? props.component.default_value
}

const currentValue = ref(getInitialValue())

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, { [props.component.id]: currentValue.value })
}

watch(currentValue, (newValue) => {
  emit('update-component-values', props.component.id, { [props.component.id]: newValue })
})

const handleChange = (value: string): void => {
  currentValue.value = value
}
</script>

<template>
  <div class="radio-group horizontal">
    <label
      v-for="[value, label] in Object.entries(component.choices)"
      :key="value"
      class="radio-option"
    >
      <input
        type="radio"
        :name="component.id"
        :value="value"
        :checked="currentValue === value"
        @change="handleChange(value)"
      />
      <span class="radio-label">{{ label }} </span>
    </label>
  </div>
</template>

<style scoped>
.radio-group.horizontal {
  display: flex;
  gap: var(--dimension-6);
  align-items: center;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  cursor: pointer;
}

.radio-option input[type='radio'] {
  margin: 0;
}

.radio-label {
  user-select: none;
}
</style>
