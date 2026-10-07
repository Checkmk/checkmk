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
  rotateIcon?: number | undefined
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
      :data-label="option.icon === undefined ? option.label : undefined"
      :disabled="isDisabled(option.disabled)"
      :title="isDisabled(option.disabled) ? option.disabledTooltip : option.tooltip"
      @click.prevent="setSelectedOption(option.value)"
    >
      <CmkMultitoneIcon
        v-if="option.icon"
        :name="option.icon"
        :rotate="option.rotateIcon"
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
  margin: 0;
  padding: 0 var(--dimension-4);
  border: 1px solid var(--border-color-subtle);
  border-radius: 0;
  background-color: var(--background-base);
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  letter-spacing: unset;
}

/* Reserves the bold width, so that selecting an option does not resize the group. */
.cmk-toggle-button-group__toggle-option[data-label] {
  flex-direction: column;

  &::after {
    content: attr(data-label);
    height: 0;
    overflow: hidden;
    visibility: hidden;
    font-weight: var(--font-weight-bold);
  }
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
  border-color: var(--border-color-default);
  background-color: var(--background-selected);
  color: var(--font-color);
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
  color: var(--font-color-disabled);
  cursor: not-allowed;
  background-color: var(--background-base);
}

.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled:hover) {
  background-color: var(--background-base);
}

/* stylelint-disable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.cmk-toggle-button-group__toggle-option:is(.cmk-toggle-button-group__disabled)
  :deep(.cmk-multitone-icon) {
  --icon-primary-color: var(--font-color-disabled);
}
/* stylelint-enable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */

.cmk-toggle-button-group__toggle-option:hover:not(
    :is(.cmk-toggle-button-group__selected, .cmk-toggle-button-group__disabled)
  ) {
  background-color: rgb(from var(--background-hover) r g b / 60%);
}

.cmk-toggle-button-group__toggle-option:not(.cmk-toggle-button-group__selected)
  + .cmk-toggle-button-group__toggle-option:not(.cmk-toggle-button-group__selected) {
  border-left-width: 0;
}
</style>
