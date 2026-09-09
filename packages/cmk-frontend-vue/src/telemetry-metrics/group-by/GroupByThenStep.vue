<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import type { Section, Suggestions } from 'cmk-ui-library/components/CmkSuggestions/types'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, onMounted, ref, useTemplateRef } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { ATTRIBUTE_KIND_ORDER, attributeKindLabel } from '../attribute-kind'
import GroupByKeysArea from './GroupByKeysArea.vue'
import { functionLabel, thenStepSummary } from './group-by-label'
import { SCALAR_FUNCTIONS } from './types'
import type { AggregationStep, AttributeKind, GroupKey, ScalarFunction } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    allowedKeys: GroupKey[]
    autoOpen?: boolean
  }>(),
  { autoOpen: false }
)

const model = defineModel<AggregationStep>({ required: true })

const emit = defineEmits<{
  (e: 'remove'): void
}>()

const summary = computed(() => thenStepSummary(model.value))
const editAriaLabel = computed(() => `${_t('Edit then step')}: ${summary.value}`)

const functionOptions: Suggestions = {
  type: 'fixed',
  suggestions: SCALAR_FUNCTIONS.map((fn) => ({ name: fn, title: functionLabel(fn) }))
}

function onFunctionUpdate(value: string | null): void {
  if (value === null) {
    return
  }
  model.value = { ...model.value, function: value as ScalarFunction }
}

function querySuggestions(query: string): Promise<Response> {
  const normalizedQuery = query.trim().toLowerCase()
  const sections: Section[] = ATTRIBUTE_KIND_ORDER.flatMap((attributeKind) => {
    const keys = props.allowedKeys.filter(
      (key) =>
        key.attributeKind === attributeKind &&
        (normalizedQuery === '' || key.attributeKey.toLowerCase().includes(normalizedQuery))
    )
    return keys.length === 0
      ? []
      : [
          {
            title: attributeKindLabel(attributeKind),
            suggestions: keys.map((key) => ({
              name: key.attributeKey,
              title: untranslated(key.attributeKey)
            }))
          }
        ]
  })
  return Promise.resolve(new Response(sections))
}

function resolveAttributeKind(key: string): AttributeKind | null {
  return (
    props.allowedKeys.find((candidate) => candidate.attributeKey === key)?.attributeKind ?? null
  )
}

const keysModel = computed<GroupKey[]>({
  get: () => model.value.keys,
  set: (keys) => {
    model.value = { ...model.value, keys }
  }
})

const editing = ref(props.autoOpen)

const functionDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('functionDropdownRef')
const keysAreaRef = useTemplateRef<InstanceType<typeof GroupByKeysArea>>('keysAreaRef')

function focusOnOpen(): void {
  void nextTick(() => {
    // A lone key is the obvious target; open it directly.
    if (model.value.keys.length === 1) {
      keysAreaRef.value?.focusKey(model.value.keys[0]!.id)
      return
    }
    functionDropdownRef.value?.focus()
  })
}

function onEdit(): void {
  editing.value = true
  focusOnOpen()
}

// A freshly added step opens straight into its function dropdown.
onMounted(() => {
  if (editing.value) {
    void nextTick(() => functionDropdownRef.value?.open())
  }
})

// Veto closing while a pending key is empty, revealing its error.
function canLeaveEdit(): boolean {
  return keysAreaRef.value?.tryChangeFocus() ?? true
}
</script>

<template>
  <InlineEditPill
    :editing="editing"
    :removable="!editing"
    :can-leave="canLeaveEdit"
    :aria-label="summary"
    :edit-aria-label="editAriaLabel"
    :remove-label="_t('Remove then step')"
    scope-marker-attr="data-gb-scope"
    item-marker-attr="data-gb-item"
    @edit="onEdit"
    @done="editing = false"
    @remove="emit('remove')"
  >
    <template #read-only>
      <span class="metric-backend-group-by-then-step__summary">
        <span class="metric-backend-group-by-then-step__segment">{{
          functionLabel(model.function)
        }}</span>
        <span
          v-if="model.keys.length === 0"
          class="metric-backend-group-by-then-step__everything"
          >{{ _t('nothing, combine all series into one') }}</span
        >
        <template v-for="(key, index) in model.keys" :key="key.id">
          <span
            v-if="key.attributeKind !== null"
            class="metric-backend-group-by-then-step__segment metric-backend-group-by-then-step__segment--dimmed"
            >[{{ attributeKindLabel(key.attributeKind) }}]</span
          >
          <span class="metric-backend-group-by-then-step__segment"
            >{{ key.attributeKey }}{{ index < model.keys.length - 1 ? ',' : '' }}</span
          >
        </template>
      </span>
    </template>
    <template #edit>
      <span class="metric-backend-group-by-then-step__segment">
        <CmkDropdown
          ref="functionDropdownRef"
          floating
          :model-value="model.function"
          :options="functionOptions"
          :label="_t('Aggregation function')"
          @update:model-value="onFunctionUpdate"
        />
      </span>
      <GroupByKeysArea
        ref="keysAreaRef"
        v-model="keysModel"
        :query-suggestions="querySuggestions"
        :can-add="allowedKeys.length > 0"
        :resolve-attribute-kind="resolveAttributeKind"
        hide-attribute-kind
        testid="then-step-keys"
      />
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-group-by-then-step__summary {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-4);
}

.metric-backend-group-by-then-step__segment {
  padding: var(--dimension-2) 0;
  display: inline-flex;
  align-items: center;
}

.metric-backend-group-by-then-step__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-group-by-then-step__everything {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
