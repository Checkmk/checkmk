<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import CmkMultitoneIcon from './CmkIcon/CmkMultitoneIcon.vue'
import type { OneColorIcons } from './CmkIcon/types'

export type ToggleButtonOption = {
  label: string
  value: string
  icon?: OneColorIcons | undefined
  tooltip?: TranslatedString | undefined
  disabled?: boolean | string | undefined
  disabledTooltip?: TranslatedString | undefined
}

export interface ToggleButtonGroupProps {
  options: ToggleButtonOption[]
  modelValue?: string | null
  spacing?: 'default' | 'none'
  size?: 'medium' | 'small'
}

const props = withDefaults(defineProps<ToggleButtonGroupProps>(), {
  spacing: 'default',
  size: 'medium'
})

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
  <div
    class="cmk-toggle-button-group__container"
    :class="[
      `cmk-toggle-button-group__container--size-${props.size}`,
      { 'cmk-toggle-button-group__container--spacing-default': props.spacing === 'default' }
    ]"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="cmk-toggle-button-group__toggle-option"
      :class="{
        'cmk-toggle-button-group__selected': isSelected(option.value),
        'cmk-toggle-button-group__disabled': isDisabled(option.disabled),
        'cmk-toggle-button-group__icon-only': option.icon !== undefined
      }"
      :aria-label="`Toggle ${option.label}`"
      :aria-pressed="isSelected(option.value)"
      :disabled="isDisabled(option.disabled)"
      :title="isDisabled(option.disabled) ? option.disabledTooltip : option.tooltip"
      @click.prevent="setSelectedOption(option.value)"
    >
      <CmkMultitoneIcon
        v-if="option.icon"
        :name="option.icon"
        primary-color="font"
        size="small"
        aria-hidden="true"
      />
      <template v-else>{{ option.label }}</template>
    </button>
  </div>
</template>

<style scoped>
.cmk-toggle-button-group__container {
  --toggle-button-group-radius: var(--dimension-3);

  width: max-content;
  max-width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.cmk-toggle-button-group__container--size-small {
  --toggle-button-group-radius: var(--dimension-2);
}

.cmk-toggle-button-group__container--spacing-default {
  margin-bottom: var(--dimension-4);
}

.cmk-toggle-button-group__toggle-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--dimension-9);
  padding: 0 var(--dimension-4);
  border: 1px solid var(--toggle-button-group-inactive-border-color);
  border-radius: 0;
  background-color: var(--toggle-button-group-inactive-bg-color);
  color: var(--toggle-button-group-inactive-text-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
}

.cmk-toggle-button-group__toggle-option:first-child {
  border-top-left-radius: var(--toggle-button-group-radius);
  border-bottom-left-radius: var(--toggle-button-group-radius);
}

.cmk-toggle-button-group__toggle-option:last-child {
  border-top-right-radius: var(--toggle-button-group-radius);
  border-bottom-right-radius: var(--toggle-button-group-radius);
}

.cmk-toggle-button-group__selected + .cmk-toggle-button-group__toggle-option {
  border-left-width: 0;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.cmk-toggle-button-group__toggle-option:has(+ .cmk-toggle-button-group__selected) {
  border-right-width: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.cmk-toggle-button-group__toggle-option:focus-visible {
  outline: revert;
  position: relative;
}

.cmk-toggle-button-group__selected {
  height: var(--dimension-10);
  border-radius: var(--toggle-button-group-radius);
  border-color: var(--toggle-button-group-border-color);
  background-color: var(--toggle-button-group-active-bg-color);
  color: var(--toggle-button-group-active-text-color);
  font-weight: var(--font-weight-bold);
}

.cmk-toggle-button-group__container--size-small .cmk-toggle-button-group__toggle-option {
  height: var(--dimension-7);
}

.cmk-toggle-button-group__container--size-small .cmk-toggle-button-group__selected {
  height: var(--dimension-8);
}

.cmk-toggle-button-group__container--size-small .cmk-toggle-button-group__icon-only {
  width: var(--dimension-8);
  padding: 0;
}

.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled) {
  color: var(--toggle-button-group-disabled-text-color);
  cursor: not-allowed;
  background-color: var(--toggle-button-group-inactive-bg-color);
}

.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled:hover) {
  background-color: var(--toggle-button-group-inactive-bg-color);
}

/* stylelint-disable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled)
  :deep(.cmk-multitone-icon) {
  --icon-primary-color: var(--toggle-button-group-disabled-text-color);
}
/* stylelint-enable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */

.cmk-toggle-button-group__toggle-option:hover:not(
    :is(.cmk-toggle-button-group__selected, .cmk-toggle-button-group__disabled)
  ) {
  background-color: rgb(from var(--toggle-button-group-hover-bg-color) r g b / 60%);
}

.cmk-toggle-button-group__toggle-option:not(.cmk-toggle-button-group__selected)
  + .cmk-toggle-button-group__toggle-option:not(.cmk-toggle-button-group__selected) {
  border-left-width: 0;
}
</style>
