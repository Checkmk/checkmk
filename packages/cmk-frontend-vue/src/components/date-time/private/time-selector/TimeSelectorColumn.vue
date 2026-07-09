<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T extends string | number">
import { useTemplateRef } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { useListboxColumn } from './useListboxColumn'

const props = defineProps<{
  /** The selectable options, in display order. */
  options: readonly T[]
  /** Accessible name of the column's listbox. Deliberately not called `ariaLabel`: a prop of
   * that name collides with the builtin `aria-label` attribute typing and breaks the inference
   * of `T` at the use sites. */
  label: TranslatedString
  /** Render an option as its display string. */
  format: (option: T) => string
}>()

const emit = defineEmits<{
  /** Arrow navigation reached past this column's edge; lets the owner move focus to a sibling column. */
  (e: 'navigate', direction: 'previous' | 'next'): void
  /** The user requested commit (Enter on an option). */
  (e: 'commit'): void
}>()

/** The selected option. */
const model = defineModel<T>({ required: true })

const scrollContainerRef = useTemplateRef('scrollContainerRef')
const listboxRef = useTemplateRef('listboxRef')

const { onKeydown, focusSelected, centerSelected } = useListboxColumn<T>({
  options: () => props.options,
  selected: model,
  scroller: () => scrollContainerRef.value?.containerRef ?? null,
  listbox: () => listboxRef.value,
  navigate: (direction) => emit('navigate', direction),
  commit: () => emit('commit')
})

defineExpose({ focusSelected, centerSelected })
</script>

<template>
  <CmkScrollContainer ref="scrollContainerRef" type="outer" max-height="256px" height="auto">
    <div ref="listboxRef" class="cmk-time-selector-column" role="listbox" :aria-label="label">
      <button
        v-for="option in options"
        :key="option"
        type="button"
        class="cmk-time-selector-column__option"
        :class="{ 'cmk-time-selector-column__option--selected': option === model }"
        role="option"
        :aria-selected="option === model"
        :tabindex="option === model ? 0 : -1"
        @click="model = option"
        @keydown="onKeydown"
      >
        {{ format(option) }}
      </button>
    </div>
  </CmkScrollContainer>
</template>

<style scoped>
.cmk-time-selector-column {
  /* Local color hooks so the later coloring pass can re-point them per theme in one place. */
  --cmk-time-selector-selected-bg: var(--color-corporate-green-50);
  --cmk-time-selector-selected-fg: var(--color-conference-grey-100);
  --cmk-time-selector-selected-border: var(--color-corporate-green-70);

  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 36px;
}

.cmk-time-selector-column__option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin: 0;
  padding: var(--dimension-3) var(--dimension-4);
  border: 1px solid transparent;
  border-radius: var(--dimension-3);
  background: transparent;
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  box-shadow: none;

  &:hover {
    background: var(--input-hover-bg-color);
  }

  &:focus-visible {
    outline: revert;
  }
}

.cmk-time-selector-column__option--selected {
  background: var(--cmk-time-selector-selected-bg);
  color: var(--cmk-time-selector-selected-fg);
  border-color: var(--cmk-time-selector-selected-border);

  &:hover {
    background: var(--cmk-time-selector-selected-bg);
  }
}
</style>
