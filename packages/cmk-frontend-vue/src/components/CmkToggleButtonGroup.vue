<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

export type ToggleButtonOption = {
  label: string
  value: string
  tooltip?: TranslatedString | undefined
  disabled?: boolean | string | undefined
  disabledTooltip?: TranslatedString | undefined
}

export interface ToggleButtonGroupProps {
  options: ToggleButtonOption[]
  modelValue?: string | null
}

const props = defineProps<ToggleButtonGroupProps>()

const emit = defineEmits({
  'update:modelValue': (_value: string) => true
})

const isSelected = (value: string) => props.modelValue !== null && value === props.modelValue
const isDisabled = (disabled: boolean | string | undefined) =>
  disabled === true || disabled === 'true'
function setSelectedOption(value: string) {
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="cmk-toggle-button-group__container">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="cmk-toggle-button-group__toggle-option"
      :class="{
        'cmk-toggle-button-group__selected': isSelected(option.value),
        'cmk-toggle-button-group__disabled': isDisabled(option.disabled)
      }"
      :aria-label="`Toggle ${option.label}`"
      :aria-pressed="isSelected(option.value)"
      :disabled="isDisabled(option.disabled)"
      :title="isDisabled(option.disabled) ? option.disabledTooltip : option.tooltip"
      @click.prevent="setSelectedOption(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.cmk-toggle-button-group__container {
  width: max-content;
  max-width: 100%;
  margin-bottom: 8px;
  padding: 5px;
  border-radius: 5px;
  border: 1px solid var(--toggle-button-group-border-color);
  background-color: var(--toggle-button-group-inactive-bg-color);
  display: flex;
  flex-wrap: wrap;
}

.cmk-toggle-button-group__toggle-option {
  height: auto;
  min-width: 150px;
  border: none;
  background-color: var(--toggle-button-group-inactive-bg-color);
  color: var(--toggle-button-group-inactive-text-color);
  margin: 0 2px;
  padding: 3px;
  font-weight: var(--font-weight-default);
}

.cmk-toggle-button-group__toggle-option:focus-visible {
  outline: revert;
}

.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled) {
  color: var(--toggle-button-group-disabled-text-color);
  cursor: not-allowed;
  background-color: var(--toggle-button-group-inactive-bg-color);
}

.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled:hover) {
  background-color: var(--toggle-button-group-inactive-bg-color);
}

.cmk-toggle-button-group__toggle-option:hover:not(
    :is(.cmk-toggle-button-group__selected, .cmk-toggle-button-group__disabled)
  ) {
  background-color: rgb(from var(--toggle-button-group-hover-bg-color) r g b / 60%);
}

.cmk-toggle-button-group__selected {
  border: 1px solid var(--toggle-button-group-border-color);
  background-color: var(--toggle-button-group-active-bg-color);
  color: var(--toggle-button-group-active-text-color);
  font-weight: var(--font-weight-bold);
}
</style>
