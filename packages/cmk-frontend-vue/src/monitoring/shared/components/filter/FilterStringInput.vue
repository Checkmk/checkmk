<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts" generic="F extends FilterField">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '../../api/types'
import type { StringInputFilter } from './types'

const { _t } = usei18n()

const props = defineProps<{ definition: StringInputFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

function extractValues(node: ColumnFilterNode<F> | undefined): string[] {
  if (!node || node.type !== 'condition') {
    return []
  }
  const values: unknown[] = Array.isArray(node.value) ? node.value : [node.value]
  return values.filter((entry): entry is string => typeof entry === 'string' && entry !== '')
}

function isExactMatch(node: ColumnFilterNode<F> | undefined): boolean {
  return node?.type === 'condition' && node.op === 'one_of'
}

// E.g. the exact host name a link from a classic view carries, as an anchored expression.
function isPattern(node: ColumnFilterNode<F> | undefined): boolean {
  return node?.type === 'condition' && node.op === 'matches'
}

function fieldText(node: ColumnFilterNode<F> | undefined): string {
  const values = extractValues(node)
  return values.length === 1 ? values[0]! : ''
}

const value = ref<string>(fieldText(model.value))

const showsExactMatch = computed(() => isExactMatch(model.value) && value.value !== '')
const showsPattern = computed(() => isPattern(model.value) && value.value !== '')

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
      return node.children.flatMap((child) => extractValues(child as ColumnFilterNode<F>))
    }
    return extractValues(node)
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
      class="monitoring-filter-string-input__element"
      field-size="medium"
      :placeholder="_t('Contains ...')"
      :aria-label="_t('Value')"
      @update:model-value="createFilterNode($event)"
    />
    <span
      v-if="!definition.suggest && showsExactMatch"
      class="monitoring-filter-string-input__hint"
    >
      {{ _t('Exact match. Editing searches by substring.') }}
    </span>
    <span v-if="!definition.suggest && showsPattern" class="monitoring-filter-string-input__hint">
      {{ _t('Regular expression. Editing searches by substring.') }}
    </span>
  </div>
</template>

<style scoped>
.monitoring-filter-string-input__container {
  margin: 0 var(--dimension-5) var(--dimension-4) var(--dimension-5);

  /* stylelint-disable-next-line selector-pseudo-class-no-unknown */
  :deep(.monitoring-filter-string-input__element) {
    width: 100%;
  }
}

.monitoring-filter-string-input__hint {
  display: block;
  margin-top: var(--dimension-3);
  color: var(--font-color-dimmed);
}
</style>
