<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import AttributeFilterPill from './AttributeFilterPill.vue'
import { operatorTakesValue } from './types'
import type {
  AttributeCondition,
  AttributeFilterModel,
  AttributeType,
  ConnectedCondition,
  Operator
} from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    querySuggestions: QuerySuggestionsFn
    queryValueSuggestions: (
      condition: AttributeCondition,
      query: string
    ) => ReturnType<QuerySuggestionsFn>
    resolveAttributeType?: ((key: string) => AttributeType) | undefined
    ariaLabel?: string | undefined
  }>(),
  { resolveAttributeType: undefined }
)

const model = defineModel<AttributeFilterModel>({ default: () => [] })

function removeCondition(target: ConnectedCondition): void {
  model.value = model.value.filter((c) => c.id !== target.id)
}

// Apply the inferred type in the same mutation as the key; only override when
// the resolver hits, so a user-picked type survives an edit into free-text.
function updateKey(target: ConnectedCondition, value: string): void {
  const inferred = props.resolveAttributeType?.(value) ?? null
  model.value = model.value.map((c) =>
    c.id === target.id
      ? { ...c, key: value, ...(inferred !== null ? { attributeType: inferred } : {}) }
      : c
  )
}

function updateAttributeType(target: ConnectedCondition, value: AttributeType): void {
  model.value = model.value.map((c) => (c.id === target.id ? { ...c, attributeType: value } : c))
}

function updateOperator(target: ConnectedCondition, value: Operator): void {
  model.value = model.value.map((c) => {
    if (c.id !== target.id) {
      return c
    }
    const clearValue = operatorTakesValue(c.operator) !== operatorTakesValue(value)
    return { ...c, operator: value, ...(clearValue ? { value: '' } : {}) }
  })
}

function updateValue(target: ConnectedCondition, value: string): void {
  model.value = model.value.map((c) => (c.id === target.id ? { ...c, value } : c))
}
</script>

<template>
  <div role="group" :aria-label="ariaLabel ?? _t('Attribute filter')">
    <AttributeFilterPill
      v-for="entry in model"
      :key="entry.id"
      :condition="entry"
      :query-suggestions="querySuggestions"
      :query-value-suggestions="queryValueSuggestions"
      removable
      @remove="removeCondition(entry)"
      @update:key="(value) => updateKey(entry, value)"
      @update:attribute-type="(value) => updateAttributeType(entry, value)"
      @update:operator="(value) => updateOperator(entry, value)"
      @update:value="(value) => updateValue(entry, value)"
    />
  </div>
</template>
