<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { randomId } from 'cmk-ui-library/lib/randomId'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { computed, nextTick, ref, watch } from 'vue'

import AttributeFilterPill from './AttributeFilterPill.vue'
import { handleArrowNav } from './focus-nav'
import { isConditionValid, operatorTakesValue } from './types'
import type {
  AttributeFilterModel,
  AttributeKind,
  Condition,
  ConditionGroup,
  Operator
} from './types'

const { _t } = usei18n()

const vClickOutside = useClickOutside()

const props = withDefaults(
  defineProps<{
    querySuggestions: (condition: Condition, query: string) => ReturnType<QuerySuggestionsFn>
    queryValueSuggestions: (condition: Condition, query: string) => ReturnType<QuerySuggestionsFn>
    suggestionRevision?: number
    resolveAttributeKind?: ((key: string) => AttributeKind | null) | undefined
    operators?: Operator[] | undefined
    allowOr?: boolean
    ariaLabel?: string | undefined
  }>(),
  { suggestionRevision: 0, resolveAttributeKind: undefined, operators: undefined, allowOr: true }
)

const model = defineModel<AttributeFilterModel>({ default: () => [] })

const editingId = ref<string | null>(null)
const enteredGroupId = ref<string | null>(null)
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

const flatConditions = computed<Condition[]>(() => model.value.flatMap((group) => group.conditions))

function freshCondition(): Condition {
  return {
    id: randomId(),
    attributeKind: null,
    key: '',
    operator: props.operators?.[0] ?? 'equals',
    value: ''
  }
}

function mapConditions(fn: (condition: Condition) => Condition): void {
  model.value = model.value.map((group) => ({ ...group, conditions: group.conditions.map(fn) }))
}

function removeCondition(target: Condition): void {
  if (editingId.value === target.id) {
    editingId.value = null
  }
  model.value = model.value
    .map((group) => ({ ...group, conditions: group.conditions.filter((c) => c.id !== target.id) }))
    .filter((group) => group.conditions.length > 0)
}

function removeGroup(group: ConditionGroup): void {
  if (editingId.value !== null && group.conditions.some((c) => c.id === editingId.value)) {
    editingId.value = null
  }
  model.value = model.value.filter((g) => g.id !== group.id)
}

// Apply the inferred type in the same mutation as the key; only override when
// the resolver hits, so a user-picked type survives an edit into free-text.
function updateKey(target: Condition, value: string): void {
  const inferred = props.resolveAttributeKind?.(value) ?? null
  mapConditions((c) =>
    c.id === target.id
      ? { ...c, key: value, ...(inferred !== null ? { attributeKind: inferred } : {}) }
      : c
  )
}

function updateAttributeKind(target: Condition, value: AttributeKind | null): void {
  mapConditions((c) => (c.id === target.id ? { ...c, attributeKind: value } : c))
}

function updateOperator(target: Condition, value: Operator): void {
  mapConditions((c) => {
    if (c.id !== target.id) {
      return c
    }
    const clearValue = operatorTakesValue(c.operator) !== operatorTakesValue(value)
    return { ...c, operator: value, ...(clearValue ? { value: '' } : {}) }
  })
}

function updateValue(target: Condition, value: string): void {
  mapConditions((c) => (c.id === target.id ? { ...c, value } : c))
}

// Operators collapsed to one choice: the per-pill dropdown is hidden, so coerce every condition onto it in a single mutation (per-pill emits would race through defineModel and lose all but the last write).
watch(
  () => [props.operators, model.value] as const,
  ([operators]) => {
    if (!operators || operators.length !== 1) {
      return
    }
    const only = operators[0]!
    if (flatConditions.value.every((c) => c.operator === only)) {
      return
    }
    mapConditions((c) => {
      if (c.operator === only) {
        return c
      }
      const clearValue = operatorTakesValue(c.operator) !== operatorTakesValue(only)
      return { ...c, operator: only, ...(clearValue ? { value: '' } : {}) }
    })
  },
  { immediate: true }
)

// AND->OR: split the group at the toggled condition.
function splitGroup(groupIndex: number, conditionIndex: number): void {
  const group = model.value[groupIndex]
  if (!group) {
    return
  }
  const left = { ...group, conditions: group.conditions.slice(0, conditionIndex) }
  const right: ConditionGroup = {
    id: randomId(),
    conditions: group.conditions.slice(conditionIndex)
  }
  model.value = [
    ...model.value.slice(0, groupIndex),
    left,
    right,
    ...model.value.slice(groupIndex + 1)
  ]
}

// OR->AND: merge the clause into its predecessor.
function mergeWithPrevious(groupIndex: number): void {
  const previous = model.value[groupIndex - 1]
  const current = model.value[groupIndex]
  if (!previous || !current) {
    return
  }
  const merged = { ...previous, conditions: [...previous.conditions, ...current.conditions] }
  model.value = [
    ...model.value.slice(0, groupIndex - 1),
    merged,
    ...model.value.slice(groupIndex + 1)
  ]
}

function addConditionLabel(condition: Condition): string {
  return condition.key
    ? _t('Add condition after %{key}', { key: condition.key })
    : _t('Add condition after previous condition')
}

function tryChangeFocus(): boolean {
  const id = editingId.value
  if (id === null) {
    return true
  }
  const condition = flatConditions.value.find((c) => c.id === id)
  if (!condition) {
    return true
  }
  if (isConditionValid(condition)) {
    return true
  }
  pillRefs.get(id)?.revealValidationErrors()
  return false
}

function addEmpty(): void {
  if (!tryChangeFocus()) {
    return
  }
  const condition = freshCondition()
  model.value = [{ id: randomId(), conditions: [condition] }]
  editingId.value = condition.id
}

function addConditionInGroup(groupIndex: number, conditionIndex: number): void {
  if (!tryChangeFocus()) {
    return
  }
  const condition = freshCondition()
  model.value = model.value.map((group, index) =>
    index === groupIndex
      ? {
          ...group,
          conditions: [
            ...group.conditions.slice(0, conditionIndex + 1),
            condition,
            ...group.conditions.slice(conditionIndex + 1)
          ]
        }
      : group
  )
  editingId.value = condition.id
}

// A + after a group (outside the box) starts a new OR clause; a + inside adds AND.
function addGroupAfter(groupIndex: number): void {
  if (!tryChangeFocus()) {
    return
  }
  const condition = freshCondition()
  const group: ConditionGroup = { id: randomId(), conditions: [condition] }
  model.value = [
    ...model.value.slice(0, groupIndex + 1),
    group,
    ...model.value.slice(groupIndex + 1)
  ]
  editingId.value = condition.id
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

function isEntered(group: ConditionGroup): boolean {
  return enteredGroupId.value === group.id
}

// Drop the entered marker when the model mutation removed or split the group it pointed at.
watch(
  () => model.value,
  (next) => {
    if (enteredGroupId.value === null) {
      return
    }
    const stillEnterable = next.some(
      (g) => g.id === enteredGroupId.value && g.conditions.length > 1
    )
    if (!stillEnterable) {
      enteredGroupId.value = null
    }
  }
)

function onGroupKeydown(event: KeyboardEvent, group: ConditionGroup): void {
  if (event.target !== event.currentTarget) {
    return
  }
  if (event.key === 'Backspace' || event.key === 'Delete') {
    event.preventDefault()
    removeGroup(group)
    return
  }
  if (event.key === ' ' || event.key === 'Enter') {
    event.preventDefault()
    enteredGroupId.value = group.id
    void nextTick(() => pillRefs.get(group.conditions[0]!.id)?.focus())
  }
}

function onGroupEscape(event: KeyboardEvent, group: ConditionGroup): void {
  if (!isEntered(group)) {
    return
  }
  event.preventDefault()
  const wrapper = event.currentTarget as HTMLElement | null
  enteredGroupId.value = null
  void nextTick(() => wrapper?.focus())
}

function onGroupClickOutside(group: ConditionGroup): void {
  if (!isEntered(group)) {
    return
  }
  enteredGroupId.value = null
}
</script>

<template>
  <div
    class="metric-backend-form-attribute-filter"
    role="group"
    :aria-label="ariaLabel ?? _t('Attribute filter')"
    @keydown.left.capture="handleArrowNav"
    @keydown.right.capture="handleArrowNav"
  >
    <CmkIconButton
      v-if="model.length === 0"
      class="metric-backend-form-attribute-filter__add"
      name="add"
      size="large"
      :title="_t('Add condition')"
      :aria-label="_t('Add condition')"
      @mousedown.prevent
      @click="addEmpty"
    />
    <template v-for="(group, groupIndex) in allowOr ? model : []" :key="group.id">
      <!-- Connectors (AND/OR) are intentionally kept untranslated:
           they have no agreed product-wide localisations yet. -->
      <button
        v-if="groupIndex > 0"
        type="button"
        class="metric-backend-form-attribute-filter__connector"
        :aria-label="_t('Toggle connector, currently %{connector}', { connector: 'OR' })"
        :title="_t('Toggle AND / OR')"
        @mousedown.prevent
        @click="mergeWithPrevious(groupIndex)"
      >
        {{ untranslated('OR') }}
      </button>
      <template v-if="group.conditions.length > 1">
        <div
          v-click-outside="() => onGroupClickOutside(group)"
          class="metric-backend-form-attribute-filter__group"
          data-testid="attribute-filter-group"
          :data-af-scope="isEntered(group) ? '' : undefined"
          :tabindex="isEntered(group) ? -1 : 0"
          :aria-label="_t('AND group of %{count} conditions', { count: group.conditions.length })"
          @keydown="(e) => onGroupKeydown(e, group)"
          @keydown.escape="(e) => onGroupEscape(e, group)"
        >
          <CmkIconButton
            class="metric-backend-form-attribute-filter__remove-group"
            name="close"
            size="small"
            data-af-item
            :tabindex="isEntered(group) ? 0 : -1"
            :title="_t('Remove group')"
            :aria-label="_t('Remove group')"
            @mousedown.prevent
            @click="removeGroup(group)"
          />
          <template v-for="(condition, conditionIndex) in group.conditions" :key="condition.id">
            <button
              v-if="conditionIndex > 0"
              type="button"
              class="metric-backend-form-attribute-filter__connector"
              data-af-item
              :tabindex="isEntered(group) ? 0 : -1"
              :aria-label="_t('Toggle connector, currently %{connector}', { connector: 'AND' })"
              :title="_t('Toggle AND / OR')"
              @mousedown.prevent
              @click="splitGroup(groupIndex, conditionIndex)"
            >
              {{ untranslated('AND') }}
            </button>
            <AttributeFilterPill
              :ref="pillRefSetter(condition.id)"
              :condition="condition"
              :operators="operators"
              :query-suggestions="querySuggestions"
              :query-value-suggestions="queryValueSuggestions"
              :suggestion-revision="suggestionRevision"
              removable
              :editing="condition.id === editingId"
              :tab-focusable="isEntered(group)"
              @remove="removeCondition(condition)"
              @edit="startEditing(condition.id)"
              @done="onEditDone(condition.id)"
              @update:key="(value) => updateKey(condition, value)"
              @update:attribute-kind="(value) => updateAttributeKind(condition, value)"
              @update:operator="(value) => updateOperator(condition, value)"
              @update:value="(value) => updateValue(condition, value)"
            />
            <CmkIconButton
              class="metric-backend-form-attribute-filter__add"
              name="add"
              size="large"
              data-af-item
              :tabindex="isEntered(group) ? 0 : -1"
              :title="_t('Add condition')"
              :aria-label="addConditionLabel(condition)"
              @mousedown.prevent
              @click="addConditionInGroup(groupIndex, conditionIndex)"
            />
          </template>
        </div>
        <!-- After-group +: starts a new OR clause. The per-pill +s inside the box add AND. -->
        <CmkIconButton
          class="metric-backend-form-attribute-filter__add"
          name="add"
          size="large"
          :title="_t('Add condition')"
          :aria-label="_t('Add condition after this group')"
          @mousedown.prevent
          @click="addGroupAfter(groupIndex)"
        />
      </template>
      <template v-else>
        <AttributeFilterPill
          :ref="pillRefSetter(group.conditions[0]!.id)"
          :condition="group.conditions[0]!"
          :operators="operators"
          :query-suggestions="querySuggestions"
          :query-value-suggestions="queryValueSuggestions"
          :suggestion-revision="suggestionRevision"
          removable
          :editing="group.conditions[0]!.id === editingId"
          @remove="removeCondition(group.conditions[0]!)"
          @edit="startEditing(group.conditions[0]!.id)"
          @done="onEditDone(group.conditions[0]!.id)"
          @update:key="(value) => updateKey(group.conditions[0]!, value)"
          @update:attribute-kind="(value) => updateAttributeKind(group.conditions[0]!, value)"
          @update:operator="(value) => updateOperator(group.conditions[0]!, value)"
          @update:value="(value) => updateValue(group.conditions[0]!, value)"
        />
        <!-- Adding to a lone pill joins it into an AND group; OR needs a second pill first. -->
        <CmkIconButton
          class="metric-backend-form-attribute-filter__add"
          name="add"
          size="large"
          :title="_t('Add condition')"
          :aria-label="addConditionLabel(group.conditions[0]!)"
          @mousedown.prevent
          @click="addConditionInGroup(groupIndex, 0)"
        />
      </template>
    </template>
    <!-- AND-only mode: flat pills joined by a static AND label, no group box or connector toggles. -->
    <template v-for="(condition, index) in allowOr ? [] : flatConditions" :key="condition.id">
      <!-- Connectors (AND) are intentionally kept untranslated:
           they have no agreed product-wide localisations yet. -->
      <span v-if="index > 0" class="metric-backend-form-attribute-filter__connector-static">
        {{ untranslated('AND') }}
      </span>
      <AttributeFilterPill
        :ref="pillRefSetter(condition.id)"
        :condition="condition"
        :operators="operators"
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        :suggestion-revision="suggestionRevision"
        removable
        :editing="condition.id === editingId"
        @remove="removeCondition(condition)"
        @edit="startEditing(condition.id)"
        @done="onEditDone(condition.id)"
        @update:key="(value) => updateKey(condition, value)"
        @update:attribute-kind="(value) => updateAttributeKind(condition, value)"
        @update:operator="(value) => updateOperator(condition, value)"
        @update:value="(value) => updateValue(condition, value)"
      />
      <CmkIconButton
        class="metric-backend-form-attribute-filter__add"
        name="add"
        size="large"
        :title="_t('Add condition')"
        :aria-label="addConditionLabel(condition)"
        @mousedown.prevent
        @click="addConditionInGroup(0, index)"
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

.metric-backend-form-attribute-filter__add:hover,
.metric-backend-form-attribute-filter__remove-group:hover {
  background-color: var(--input-hover-bg-color);
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
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-4);
  color: var(--button-form-text-color);
  cursor: pointer;
  font: inherit;
  padding: 1px 6px;
}

.metric-backend-form-attribute-filter__connector:hover {
  background-color: var(--input-hover-bg-color);
}

.metric-backend-form-attribute-filter__connector-static {
  flex-shrink: 0;
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-form-attribute-filter__connector:focus-visible {
  outline: revert;
}
</style>
