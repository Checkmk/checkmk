<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
export type ToggleButtonOption = {
  label: string
  value: string
  disabled?: boolean | string | undefined
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
function setSelectedOption(value: string) {
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="toggle_buttons_container">
    <button
      v-for="option in options"
      :key="option.value"
      class="toggle_option"
      :class="{
        selected: isSelected(option.value),
        disabled: option.disabled === true || option.disabled === 'true'
      }"
      :aria-label="`Toggle ${option.label}`"
      :disabled="option.disabled === true || option.disabled === 'true'"
      @click.prevent="setSelectedOption(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.toggle_buttons_container {
  width: max-content;
  margin-bottom: 8px;
  padding: 5px;
  border-radius: 5px;
  border: 1px solid var(--toggle-button-group-border-color);
  background-color: var(--toggle-button-group-inactive-bg-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.toggle_option {
  height: auto;
  min-width: 150px;
  border: none;
  background-color: var(--toggle-button-group-inactive-bg-color);
  color: var(--toggle-button-group-inactive-text-color);
  margin: 0 2px;
  padding: 3px;
  font-weight: var(--font-weight-default);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.toggle_option:is(:disabled) {
  color: var(--toggle-button-group-disabled-text-color);
  cursor: not-allowed;
  background-color: var(--toggle-button-group-inactive-bg-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.toggle_option:is(:disabled:hover) {
  background-color: var(--toggle-button-group-inactive-bg-color);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.toggle_option:hover:not(:is(.selected, .disabled)) {
  background-color: rgb(from var(--toggle-button-group-hover-bg-color) r g b / 60%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.selected {
  border: 1px solid var(--toggle-button-group-border-color);
  background-color: var(--toggle-button-group-active-bg-color);
  color: var(--toggle-button-group-active-text-color);
  font-weight: var(--font-weight-bold);
}
</style>
