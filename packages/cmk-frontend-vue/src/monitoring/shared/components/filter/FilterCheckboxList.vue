<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Content component for the "checkbox-list" filter type. It owns all of its own
state — search text, visible options, the tri-state "select all" and the
selection itself (via v-model). The parent `FilterDropdown` only provides the
popover shell and keyboard navigation between focusable rows.

The v-model is a `ColumnFilterNode<F>` (or undefined for "no filter"). Internally
the component works with the extracted string array for checkbox rendering and
produces a typed `one_of` condition when the selection changes.
-->
<script setup lang="ts" generic="F extends FilterField">
import { computed, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import type { CheckboxListFilter } from './types'

type SelectAllState = 'checked' | 'indeterminate' | 'unchecked'

const DEFAULT_SEARCH_THRESHOLD = 8

const SELECT_ALL_MODEL_VALUE: Record<SelectAllState, boolean | 'indeterminate'> = {
  checked: true,
  indeterminate: 'indeterminate',
  unchecked: false
}

const props = defineProps<{ definition: CheckboxListFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const { _t } = usei18n()

const searchText = ref('')

function extractValues(node: ColumnFilterNode<F> | undefined): string[] {
  if (!node || node.type !== 'condition') {
    return []
  }
  return Array.isArray(node.value) ? (node.value as string[]) : []
}

const selectedValues = computed(() => extractValues(model.value))
const selectedSet = computed(() => new Set(selectedValues.value))

const showSearch = computed(
  () =>
    props.definition.options.length > (props.definition.searchThreshold ?? DEFAULT_SEARCH_THRESHOLD)
)

const visibleOptions = computed(() => {
  const needle = searchText.value.trim().toLowerCase()
  if (!needle) {
    return props.definition.options
  }
  return props.definition.options.filter(
    (option) =>
      option.title.toLowerCase().includes(needle) || option.value.toLowerCase().includes(needle)
  )
})

const selectAllState = computed<SelectAllState>(() => {
  const total = visibleOptions.value.length
  if (total === 0) {
    return 'unchecked'
  }
  const picked = visibleOptions.value.filter((option) => selectedSet.value.has(option.value)).length
  if (picked === 0) {
    return 'unchecked'
  }
  return picked === total ? 'checked' : 'indeterminate'
})

const selectAllModelValue = computed(() => SELECT_ALL_MODEL_VALUE[selectAllState.value])

function setValues(values: string[]): void {
  if (values.length === 0) {
    model.value = undefined
  } else {
    model.value = {
      type: 'condition',
      field: props.definition.field,
      op: 'one_of',
      value: values
    } as ColumnFilterNode<F>
  }
}

function toggleOption(value: string): void {
  const next = new Set(selectedSet.value)
  if (next.has(value)) {
    next.delete(value)
  } else {
    next.add(value)
  }
  setValues([...next])
}

function toggleAll(): void {
  const next = new Set(selectedSet.value)
  if (selectAllState.value === 'checked') {
    visibleOptions.value.forEach((option) => next.delete(option.value))
  } else {
    visibleOptions.value.forEach((option) => next.add(option.value))
  }
  setValues([...next])
}

// Escape clears a non-empty search field but keeps the dropdown open; an empty
// field lets the event bubble to the dropdown's Escape handler, which closes it.
function onSearchEscape(event: KeyboardEvent): void {
  if (searchText.value) {
    searchText.value = ''
    event.stopPropagation()
  }
}
</script>

<template>
  <div class="monitoring-filter-checkbox-list">
    <input
      v-if="showSearch"
      v-model="searchText"
      type="text"
      class="monitoring-filter-checkbox-list__search"
      :placeholder="_t('Filter values')"
      :aria-label="_t('Filter values')"
      @keydown.escape="onSearchEscape"
    />

    <div class="monitoring-filter-checkbox-list__row monitoring-filter-checkbox-list__row--all">
      <CmkCheckbox
        allow-indeterminate
        :model-value="selectAllModelValue"
        :label="_t('Select all')"
        padding="top"
        @update:model-value="toggleAll"
      />
    </div>

    <div class="monitoring-filter-checkbox-list__options">
      <div
        v-for="option in visibleOptions"
        :key="option.value"
        class="monitoring-filter-checkbox-list__row"
      >
        <CmkCheckbox
          :model-value="selectedSet.has(option.value)"
          :label="untranslated(option.title)"
          padding="top"
          @update:model-value="toggleOption(option.value)"
        />
      </div>

      <p v-if="visibleOptions.length === 0" class="monitoring-filter-checkbox-list__empty">
        {{ _t('No matching values') }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.monitoring-filter-checkbox-list {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.monitoring-filter-checkbox-list__search {
  box-sizing: border-box;
  width: 100%;
  margin: 0;
  padding: var(--dimension-2) var(--dimension-4);
  font: inherit;
  color: var(--font-color);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 2px;

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 1px;
  }
}

.monitoring-filter-checkbox-list__options {
  display: flex;
  flex-direction: column;
  max-height: 240px;
  overflow-y: auto;
}

.monitoring-filter-checkbox-list__row {
  display: flex;
  align-items: center;
  padding: 0 var(--dimension-4);

  &:hover,
  &:focus-within {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-filter-checkbox-list__row--all {
  border-bottom: 1px solid var(--ux-theme-4);
  font-weight: var(--font-weight-bold);
}

.monitoring-filter-checkbox-list__empty {
  padding: var(--dimension-2) var(--dimension-4);
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
