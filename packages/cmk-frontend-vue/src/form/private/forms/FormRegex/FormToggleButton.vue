<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { ToggleButtonGroupProps } from '@/components/CmkToggleButtonGroup.vue'

const { _t } = usei18n()
defineProps<{
  modelValue?: ToggleButtonGroupProps['modelValue']
}>()

const emit = defineEmits(['update:modelValue'])

const toggleOptions = [
  { label: _t('Regex'), value: 'regex' },
  { label: _t('Text'), value: 'text' }
]
</script>

<template>
  <div class="form-toggle-button">
    <button
      v-for="option in toggleOptions ?? []"
      :key="option.value"
      :class="{ 'form-toggle-button--active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      @click.prevent="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.form-toggle-button {
  display: inline-flex;
  align-items: center;
  background-color: var(--ux-theme-0);
  border: 1px solid var(--color-mid-grey-60);
  gap: 2px;
  padding: 0 3px;
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
  height: 20px;
  z-index: +1;
}

.form-toggle-button button {
  border: none;
  color: var(--font-color);
  background-color: var(--ux-theme-0);
  font-weight: var(--font-weight-default);
  transition: all 0.2s ease-in-out;
  border-radius: 12px;
  padding: 1px 3px;
  margin: 0;
  font-size: var(--font-size-normal);
  height: 16px;
}

.form-toggle-button .form-toggle-button--active {
  background-color: var(--color-mid-grey-20);
  color: var(--color-conference-grey-100);
}
</style>
