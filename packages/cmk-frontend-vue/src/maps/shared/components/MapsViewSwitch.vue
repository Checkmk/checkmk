<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Which of two drawings of the same data is on screen -- the map list as cards or
as a table, the folder tree as a list or as a treemap.

Toolbar-scale on purpose: ``CmkToggleButtonGroup`` is the form-scale control
(150px per option, its own frame) and at that size a two-way view switch is the
loudest thing in the bar while being the least used. This is the same quiet
vocabulary the bars' other own controls use -- a recessed track on the theme's
own greys, the active side on the primary accent.
-->
<script setup lang="ts" generic="T extends string">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export interface ViewSwitchOption<T extends string = string> {
  label: TranslatedString
  value: T
}

// Generic over the value, so each bar keeps its own drawing type end to end and
// nothing has to narrow a plain string back on the way out.
const props = defineProps<{
  modelValue: T
  options: ViewSwitchOption<T>[]
  /** What the switch as a whole is for, for anyone not seeing the two labels. */
  label: TranslatedString
}>()

const emit = defineEmits<{
  'update:modelValue': [value: T]
}>()
</script>

<template>
  <div class="maps-view-switch" role="group" :aria-label="label">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="maps-view-switch__option"
      :class="{
        'maps-view-switch__option--active': option.value === props.modelValue
      }"
      :aria-pressed="option.value === props.modelValue"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.maps-view-switch {
  display: inline-flex;
  gap: var(--dimension-2);
  padding: var(--dimension-2);
  background: var(--ux-theme-4);
  border-radius: 6px;
}

.maps-view-switch__option {
  height: 20px;
  padding: 0 var(--dimension-4);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  line-height: 1;
  color: var(--font-color-dimmed);
  background: none;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.maps-view-switch__option:hover:not(.maps-view-switch__option--active) {
  color: var(--font-color);
}

.maps-view-switch__option--active {
  font-weight: var(--font-weight-bold);
  color: var(--button-primary-text-color);
  background: var(--default-button-primary-color);
}
</style>
