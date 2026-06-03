<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

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
  Connector,
  Operator
} from './types'

type FilterGroup = { entries: ConnectedCondition[]; startIndex: number }

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

function relinkHead(next: ConnectedCondition[]): void {
  if (next.length > 0) {
    next[0] = { ...next[0]!, connector: null }
  }
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
  if (idx === 0) {
    relinkHead(next)
  }
  model.value = next
}

function removeGroup(group: FilterGroup): void {
  const ids = new Set(group.entries.map((e) => e.id))
  if (editingId.value !== null && ids.has(editingId.value)) {
    editingId.value = null
  }
  const next = model.value.filter((c) => !ids.has(c.id))
  if (group.startIndex === 0) {
    relinkHead(next)
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

const groups = computed<FilterGroup[]>(() => {
  const result: FilterGroup[] = []
  model.value.forEach((entry, idx) => {
    if (entry.connector === 'OR' || result.length === 0) {
      result.push({ entries: [entry], startIndex: idx })
    } else {
      result[result.length - 1]!.entries.push(entry)
    }
  })
  return result
})

function toggleConnector(target: ConnectedCondition): void {
  model.value = model.value.map((c) => {
    if (c.id !== target.id || c.connector === null) {
      return c
    }
    return { ...c, connector: c.connector === 'OR' ? 'AND' : 'OR' }
  })
}

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

function addCondition(index: number, connector: Connector | null): void {
  if (!tryChangeFocus()) {
    return
  }
  const fresh: ConnectedCondition = {
    id: crypto.randomUUID(),
    attributeType: null,
    key: '',
    operator: 'eq',
    value: '',
    connector
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
      @click="addCondition(0, null)"
    />
    <template v-for="(group, groupIndex) in groups" :key="group.entries[0]!.id">
      <!-- Connectors (AND/OR) are intentionally kept untranslated:
           they have no agreed product-wide localisations yet. -->
      <button
        v-if="groupIndex > 0"
        type="button"
        class="metric-backend-form-attribute-filter__connector"
        :aria-label="
          _t('Toggle connector, currently %{connector}', {
            connector: group.entries[0]!.connector!
          })
        "
        :title="_t('Toggle AND / OR')"
        @mousedown.prevent
        @click="toggleConnector(group.entries[0]!)"
      >
        {{ untranslated(group.entries[0]!.connector!) }}
      </button>
      <div
        class="metric-backend-form-attribute-filter__group"
        :class="{
          'metric-backend-form-attribute-filter__group--singleton': group.entries.length === 1
        }"
        :data-testid="group.entries.length > 1 ? 'attribute-filter-group' : undefined"
      >
        <CmkIconButton
          v-if="group.entries.length > 1"
          class="metric-backend-form-attribute-filter__remove-group"
          name="close"
          size="small"
          :title="_t('Remove group')"
          :aria-label="_t('Remove group')"
          @mousedown.prevent
          @click="removeGroup(group)"
        />
        <template v-for="(entry, entryIndex) in group.entries" :key="entry.id">
          <button
            v-if="entryIndex > 0"
            type="button"
            class="metric-backend-form-attribute-filter__connector"
            :aria-label="
              _t('Toggle connector, currently %{connector}', {
                connector: entry.connector!
              })
            "
            :title="_t('Toggle AND / OR')"
            @mousedown.prevent
            @click="toggleConnector(entry)"
          >
            {{ untranslated(entry.connector!) }}
          </button>
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
            v-if="group.entries.length > 1"
            class="metric-backend-form-attribute-filter__add"
            name="add"
            size="large"
            :title="_t('Add condition')"
            :aria-label="addConditionLabel(entry)"
            @mousedown.prevent
            @click="addCondition(group.startIndex + entryIndex + 1, 'AND')"
          />
        </template>
      </div>
      <CmkIconButton
        class="metric-backend-form-attribute-filter__add"
        name="add"
        size="large"
        :title="_t('Add condition')"
        :aria-label="
          group.entries.length > 1
            ? _t('Add condition after this group')
            : addConditionLabel(group.entries[0]!)
        "
        @mousedown.prevent
        @click="addCondition(group.startIndex + group.entries.length, 'OR')"
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

.metric-backend-form-attribute-filter__group {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3) var(--dimension-4);
  padding: var(--dimension-2);
  border: 1px solid var(--success);
  border-radius: 5px;
  position: relative;
}

/* Keep the wrapper in the DOM (so the group structure is uniform) but flatten layout. */
.metric-backend-form-attribute-filter__group--singleton {
  display: contents;
}

/* Anchored top-left to keep the destructive remove far from the right-edge `+` controls. */
.metric-backend-form-attribute-filter__remove-group {
  position: absolute;
  top: 0;
  left: 0;
  transform: translate(-50%, -50%);
  background: var(--default-bg-color);
  opacity: 0;
  transition: opacity 0.15s ease-in-out;
}

.metric-backend-form-attribute-filter__group:hover
  .metric-backend-form-attribute-filter__remove-group,
.metric-backend-form-attribute-filter__group:focus-within
  .metric-backend-form-attribute-filter__remove-group {
  opacity: 1;
}

.metric-backend-form-attribute-filter__connector {
  flex-shrink: 0;
  appearance: none;
  background-color: var(--default-button-form-color);
  border: 1px solid var(--button-form-border-color);
  color: var(--button-form-text-color);
  cursor: pointer;
  font: inherit;
  padding: 1px 6px;
}

.metric-backend-form-attribute-filter__connector:hover {
  background-color: var(--input-hover-bg-color);
}

.metric-backend-form-attribute-filter__connector:focus-visible {
  outline: revert;
}
</style>
