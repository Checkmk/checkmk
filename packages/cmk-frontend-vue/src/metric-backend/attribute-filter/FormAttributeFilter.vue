<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkIconButton from '@/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import AttributeFilterPill from './AttributeFilterPill.vue'
import { isConditionValid, operatorTakesValue } from './types'
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

const editingId = ref<string | null>(null)
const pillRefs = new Map<string, InstanceType<typeof AttributeFilterPill>>()

// Cache one setter per pill id so :ref does not see a new function every render
// and re-run the setter on every model mutation.
const pillRefSetters = new Map<string, (el: unknown) => void>()
function pillRefSetter(id: string): (el: unknown) => void {
  let fn = pillRefSetters.get(id)
  if (!fn) {
    fn = (el: unknown) => {
      if (el) {
        pillRefs.set(id, el as InstanceType<typeof AttributeFilterPill>)
      } else {
        pillRefs.delete(id)
        pillRefSetters.delete(id)
      }
    }
    pillRefSetters.set(id, fn)
  }
  return fn
}

function removeCondition(target: ConnectedCondition): void {
  if (editingId.value === target.id) {
    editingId.value = null
  }
  const idx = model.value.findIndex((c) => c.id === target.id)
  if (idx < 0) {
    return
  }
  const next = model.value.filter((c) => c.id !== target.id)
  if (idx === 0 && next.length > 0) {
    next[0] = { ...next[0]!, connector: null }
  }
  model.value = next
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

// Distinguish per-pill add buttons in screen readers via positional aria-label.
function addConditionLabel(entry: ConnectedCondition): string {
  return entry.key
    ? _t('Add condition after %{key}', { key: entry.key })
    : _t('Add condition after previous condition')
}

function tryChangeFocus(): boolean {
  const id = editingId.value
  if (id === null) {
    return true
  }
  const cond = model.value.find((c) => c.id === id)
  if (!cond) {
    return true
  }
  if (isConditionValid(cond)) {
    return true
  }
  pillRefs.get(id)?.revealValidationErrors()
  return false
}

function addCondition(index: number): void {
  if (!tryChangeFocus()) {
    return
  }
  const fresh: ConnectedCondition = {
    id: crypto.randomUUID(),
    attributeType: null,
    key: '',
    operator: 'eq',
    value: '',
    connector: index === 0 ? null : 'OR'
  }
  model.value = [...model.value.slice(0, index), fresh, ...model.value.slice(index)]
  editingId.value = fresh.id
}

function startEditing(id: string): void {
  if (!tryChangeFocus()) {
    return
  }
  editingId.value = id
}

function onEditDone(id: string): void {
  if (editingId.value === id) {
    editingId.value = null
  }
}
</script>

<template>
  <div
    class="metric-backend-form-attribute-filter"
    role="group"
    :aria-label="ariaLabel ?? _t('Attribute filter')"
  >
    <CmkIconButton
      v-if="model.length === 0"
      class="metric-backend-form-attribute-filter__add"
      name="add"
      size="large"
      :title="_t('Add condition')"
      :aria-label="_t('Add condition')"
      @mousedown.prevent
      @click="addCondition(0)"
    />
    <template v-for="(entry, index) in model" :key="entry.id">
      <!-- Connectors (AND/OR) are intentionally kept untranslated:
           they have no agreed product-wide localisations yet. -->
      <span
        v-if="entry.connector !== null"
        class="metric-backend-form-attribute-filter__connector"
        :aria-label="_t('Connector')"
      >
        {{ untranslated(entry.connector) }}
      </span>
      <AttributeFilterPill
        :ref="pillRefSetter(entry.id)"
        :condition="entry"
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        removable
        :editing="entry.id === editingId"
        @remove="removeCondition(entry)"
        @edit="startEditing(entry.id)"
        @done="onEditDone(entry.id)"
        @update:key="(value) => updateKey(entry, value)"
        @update:attribute-type="(value) => updateAttributeType(entry, value)"
        @update:operator="(value) => updateOperator(entry, value)"
        @update:value="(value) => updateValue(entry, value)"
      />
      <CmkIconButton
        class="metric-backend-form-attribute-filter__add"
        name="add"
        size="large"
        :title="_t('Add condition')"
        :aria-label="addConditionLabel(entry)"
        @mousedown.prevent
        @click="addCondition(index + 1)"
      />
    </template>
  </div>
</template>

<style scoped>
.metric-backend-form-attribute-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3) var(--dimension-4);
}

.metric-backend-form-attribute-filter__connector {
  flex-shrink: 0;
  color: var(--font-color-dimmed);
  padding: 1px 3px;
}
</style>
