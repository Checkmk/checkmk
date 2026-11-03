<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import { inputSizes } from './sizes'

export interface MultiselectListItem {
  name: string
  title: TranslatedString
}

const { _t } = usei18n()

/** Up to this many items the list hugs them, beyond it scrolls; from it on it is searchable. */
const VISIBLE_ITEMS = 9

const {
  items,
  label,
  emptyText,
  fieldSize = 'large'
} = defineProps<{
  items: readonly MultiselectListItem[]
  /** The accessible name of the list. */
  label: TranslatedString
  /** Shown when the search matches no item. */
  emptyText?: TranslatedString | undefined
  /** The width, as the one of an input field of this size. */
  fieldSize?: keyof typeof inputSizes
}>()

/** The names of the selected items, always in the order of `items`. */
const selected = defineModel<string[]>({ required: true })

const query = ref('')

const searchable = computed(() => items.length >= VISIBLE_ITEMS)

const shownItems = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return items.filter(({ title }) => title.toLowerCase().includes(needle))
})

// Taken from all items rather than the matching ones, so that searching does not resize the list.
const visibleRows = computed(() => Math.max(1, Math.min(items.length, VISIBLE_ITEMS)))

const width = computed(() => inputSizes[fieldSize].width)

function select(name: string, checked: boolean): void {
  selected.value = items
    .map((item) => item.name)
    .filter((itemName) => (itemName === name ? checked : selected.value.includes(itemName)))
}
</script>

<template>
  <div class="cmk-multiselect-list" role="group" :aria-label="label">
    <div v-if="searchable" class="cmk-multiselect-list__search">
      <CmkSearchInput
        v-model="query"
        :placeholder="_t('Search...')"
        :aria-label="_t('Search %{list}', { list: label })"
        :show-submit-button="false"
      />
    </div>
    <ul class="cmk-multiselect-list__items" :style="{ '--cmk-multiselect-list-rows': visibleRows }">
      <li v-for="item in shownItems" :key="item.name" class="cmk-multiselect-list__item">
        <CmkCheckbox
          :model-value="selected.includes(item.name)"
          :label="item.title"
          padding="top"
          @update:model-value="(checked: boolean) => select(item.name, checked)"
        />
      </li>
      <li v-if="shownItems.length === 0" class="cmk-multiselect-list__empty">
        {{ emptyText ?? _t('No matching items') }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cmk-multiselect-list {
  --cmk-multiselect-list-row-height: 24px;
  --cmk-multiselect-list-hover-bg-color: var(--color-conference-grey-10);

  display: flex;
  flex-direction: column;
  width: v-bind('width');
  max-width: 100%;
  box-sizing: border-box;
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
}

.cmk-multiselect-list__search {
  padding: var(--dimension-4);
  border-bottom: 1px solid var(--default-form-element-border-color);
}

.cmk-multiselect-list__items {
  height: calc(var(--cmk-multiselect-list-rows) * var(--cmk-multiselect-list-row-height));
  margin: 0;
  padding: var(--dimension-3) 0;
  overflow-y: auto;
  list-style: none;
}

.cmk-multiselect-list__item {
  display: flex;
  align-items: center;
  height: var(--cmk-multiselect-list-row-height);
  padding: 0 var(--dimension-4);
  box-sizing: border-box;

  &:hover {
    background-color: var(--cmk-multiselect-list-hover-bg-color);
  }
}

.cmk-multiselect-list__empty {
  padding: 0 var(--dimension-4);
  color: var(--font-color-dimmed);
}

body[data-theme='modern-dark'] .cmk-multiselect-list {
  --cmk-multiselect-list-hover-bg-color: var(--color-white-10);
}
</style>
