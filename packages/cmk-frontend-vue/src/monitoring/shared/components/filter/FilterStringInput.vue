<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts" generic="F extends FilterField">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { computed, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '../../api/types'
import type { StringInputFilter } from './types'

const props = defineProps<{ definition: StringInputFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

function extractValues(node: ColumnFilterNode<F> | undefined): string {
  if (!node || node.type !== 'condition') {
    return ''
  }
  return typeof node.value === 'string' ? node.value : ''
}

const value = ref<string>(extractValues(model.value))

function containsNode(text: string): ColumnFilterNode<F> {
  return {
    type: 'condition',
    field: props.definition.field,
    op: 'contains',
    value: text
  } as ColumnFilterNode<F>
}

function createFilterNode(raw: string | undefined): void {
  const trimmed = (raw ?? '').trim()
  model.value = trimmed === '' ? undefined : containsNode(trimmed)
}

// One picked value is a "contains" of it; several are an "or" of one each, so a
// column whose values are known reads the same to the API as a typed-in one.
const selected = computed<string[]>({
  get() {
    const node = model.value
    if (!node) {
      return []
    }
    if (node.type === 'or') {
      return node.children.map((child) => extractValues(child as ColumnFilterNode<F>))
    }
    const single = extractValues(node)
    return single === '' ? [] : [single]
  },
  set(values: string[]) {
    const kept = values.filter((entry) => entry.trim() !== '')
    if (kept.length === 0) {
      model.value = undefined
      return
    }
    if (kept.length === 1) {
      createFilterNode(kept[0])
      return
    }
    model.value = {
      type: 'or',
      children: kept.map((entry) => containsNode(entry))
    }
  }
})
</script>

<template>
  <div class="monitoring-filter-string-input__container">
    <CmkChipAutocomplete
      v-if="definition.suggest"
      v-model="selected"
      :suggest="definition.suggest"
      :suggest-when-empty="definition.suggestWhenEmpty"
      :key-value="definition.keyValue"
      :wildcard-option="definition.wildcardOption"
      :max-selected="definition.maxSelected"
    />
    <CmkInput
      v-else
      v-model="value"
      field-size="medium"
      @update:model-value="createFilterNode($event)"
    />
  </div>
</template>

<style scoped>
.monitoring-filter-string-input__container {
  margin: 4px 2px;
}
</style>
