<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type ComputedRef, computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIcon from '@/components/CmkIcon'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

import type { TagFilterConfig } from '../../../types.ts'

interface TagMatchItem {
  group: string | null
  operator: string
  value: string | null
}

interface Props {
  component: TagFilterConfig
}

const props = defineProps<Props>()
// TODO: may have to handle when values are incomplete (partial)
const componentValues = defineModel<TagMatchItem[]>('componentValues', {
  required: true,
  default: () => []
})

const { _t } = usei18n()

const operatorChoices = [
  { name: 'is', value: 'is', title: untranslated('=') },
  { name: 'isnot', value: 'isnot', title: untranslated('≠') }
]

const numberOfRows = computed(() => {
  const minRows = props.component.display_rows
  const currentRows = componentValues.value.length
  return Math.max(minRows, currentRows)
})

const ensureArraySize = (minSize: number): void => {
  const currentSize = componentValues.value.length
  if (currentSize < minSize) {
    const newItems: TagMatchItem[] = []
    for (let i = currentSize; i < minSize; i++) {
      newItems.push({
        group: null,
        operator: 'is',
        value: null
      })
    }
    componentValues.value = [...componentValues.value, ...newItems]
  }
}

const getTagGroupValue = (index: number): string | null => {
  ensureArraySize(index + 1)
  return componentValues.value[index]?.group ?? null
}

const getOperatorValue = (index: number): string => {
  ensureArraySize(index + 1)
  return componentValues.value[index]?.operator ?? 'is'
}

const getTagValue = (index: number): string | null => {
  ensureArraySize(index + 1)
  return componentValues.value[index]?.value ?? null
}

const updateTagGroup = (index: number, value: string | null): void => {
  ensureArraySize(index + 1)
  const updatedItems = [...componentValues.value]
  updatedItems[index] = {
    value: updatedItems[index]!.value,
    operator: updatedItems[index]!.operator,
    group: value
  }
  componentValues.value = updatedItems
}

const updateOperator = (index: number, value: string | null): void => {
  ensureArraySize(index + 1)
  const updatedItems = [...componentValues.value]
  updatedItems[index] = {
    group: updatedItems[index]!.group,
    value: updatedItems[index]!.value,
    operator: value!
  }
  componentValues.value = updatedItems
}

const updateTagValue = (index: number, value: string | null): void => {
  ensureArraySize(index + 1)
  const updatedItems = [...componentValues.value]
  updatedItems[index] = {
    group: updatedItems[index]!.group,
    operator: updatedItems[index]!.operator,
    value: value
  }
  componentValues.value = updatedItems
}

const clearRow = (index: number): void => {
  ensureArraySize(index + 1)
  const updatedItems = [...componentValues.value]
  updatedItems[index] = {
    group: null,
    operator: 'is',
    value: null
  }
  componentValues.value = updatedItems
}

const hasAnyValue = (index: number): boolean => {
  const item = componentValues.value[index]
  return !!(item?.group || item?.value || (item?.operator && item.operator !== 'is'))
}

const groupAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'tag_groups',
    params: {
      strict: true,
      escape_regex: false
    }
  }
}

const getTagAutocompleter = (index: number): ComputedRef<Autocompleter> =>
  computed(() => ({
    fetch_method: 'ajax_vs_autocomplete',
    data: {
      ident: 'tag_groups_opt',
      params: {
        strict: true,
        group_id: getTagGroupValue(index),
        escape_regex: false
      }
    }
  }))
</script>

<template>
  <div class="db-tag-match-component">
    <template v-for="index in numberOfRows" :key="index - 1">
      <div class="db-tag-match-component__group">
        <FormAutocompleter
          :model-value="getTagGroupValue(index - 1)"
          :autocompleter="groupAutocompleter"
          :placeholder="_t('Select group...')"
          :size="20"
          :width="`fill`"
          @update:model-value="(value: string | null) => updateTagGroup(index - 1, value)"
        />
      </div>
      <div class="db-tag-match-component__operator">
        <CmkDropdown
          :options="{ type: 'fixed', suggestions: operatorChoices }"
          :label="_t('Operator')"
          :selected-option="getOperatorValue(index - 1)"
          @update:selected-option="(value: string | null) => updateOperator(index - 1, value)"
        />
      </div>
      <div class="db-tag-match-component__value">
        <FormAutocompleter
          :model-value="getTagValue(index - 1)"
          :autocompleter="getTagAutocompleter(index - 1).value"
          :placeholder="_t('Select value...')"
          :size="20"
          :width="`fill`"
          @update:model-value="(value: string | null) => updateTagValue(index - 1, value)"
        />
      </div>
      <div class="db-tag-match-component__clear">
        <button
          v-if="hasAnyValue(index - 1)"
          type="button"
          class="db-tag-match-component__clear-button"
          @click="clearRow(index - 1)"
        >
          <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
        </button>
        <div v-else class="db-tag-match-component__clear-spacer"></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.db-tag-match-component {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto;
  gap: var(--dimension-4);
}

.db-tag-match-component__group,
.db-tag-match-component__value {
  min-width: 0;
}

.db-tag-match-component__clear {
  display: flex;
  justify-content: center;
}

.db-tag-match-component__clear-button {
  width: var(--dimension-7);
  height: var(--dimension-7);
  color: var(--font-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  margin: 0;
  padding: var(--dimension-4) var(--dimension-5);
}

.db-tag-match-component__clear-spacer {
  width: var(--dimension-10);
  height: var(--dimension-7);
}
</style>
