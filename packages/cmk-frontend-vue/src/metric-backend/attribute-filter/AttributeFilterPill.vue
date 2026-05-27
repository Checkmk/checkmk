<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import { ATTRIBUTE_TYPE_LABELS, operatorPhrase, pillLabel } from './pill-label'
import { EXISTENCE_OPERATORS, STRING_OPERATORS, isOperator, operatorTakesValue } from './types'
import type { AttributeCondition, AttributeType, Operator } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    condition: AttributeCondition
    querySuggestions: QuerySuggestionsFn
    queryValueSuggestions: (
      condition: AttributeCondition,
      query: string
    ) => ReturnType<QuerySuggestionsFn>
    ariaLabel?: string | undefined
    removable?: boolean
  }>(),
  { removable: false }
)

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'update:key', value: string): void
  (e: 'update:attributeType', value: AttributeType): void
  (e: 'update:operator', value: Operator): void
  (e: 'update:value', value: string): void
}>()

const fullLabel = computed(() => pillLabel(props.condition))
const showValue = computed(() => operatorTakesValue(props.condition.operator))

const valueOptions = computed(() => ({
  type: 'callback-filtered' as const,
  querySuggestions: (query: string) => props.queryValueSuggestions(props.condition, query)
}))

const attributeTypeEmpty = computed(() => props.condition.attributeType === null)
const keyEmpty = computed(() => !props.condition.key)
const valueEmpty = computed(() => props.condition.value === '')

// A pristine pill (fresh + click) should not pre-emptively flag empties as invalid.
const isPristine = computed(
  () =>
    props.condition.attributeType === null && !props.condition.key && props.condition.value === ''
)

const valueDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('valueDropdownRef')
const pendingValueOpen = ref(false)

function onKeyUpdate(value: string | null): void {
  emit('update:key', value ?? '')
}

function onValueUpdate(value: string | null): void {
  emit('update:value', value ?? '')
}

function onOperatorUpdate(value: string | null): void {
  if (value === null || !isOperator(value)) {
    return
  }
  const prevOperatorTookValue = operatorTakesValue(props.condition.operator)
  emit('update:operator', value)
  if (!operatorTakesValue(value)) {
    return
  }
  if (prevOperatorTookValue && props.condition.value !== '') {
    return
  }
  if (prevOperatorTookValue) {
    valueDropdownRef.value?.open()
  } else {
    pendingValueOpen.value = true
  }
}

// flush:'post' so the v-if-mounted value <CmkDropdown> ref is populated before we call `open()`.
watch(
  showValue,
  (next, prev) => {
    if (!next || prev || !pendingValueOpen.value) {
      return
    }
    pendingValueOpen.value = false
    valueDropdownRef.value?.open()
  },
  { flush: 'post' }
)

const attributeTypeInput = computed<string | null>({
  get: () => props.condition.attributeType,
  set: (value) => {
    const valid =
      value !== null && Object.prototype.hasOwnProperty.call(ATTRIBUTE_TYPE_LABELS, value)
        ? (value as AttributeType)
        : null
    emit('update:attributeType', valid)
  }
})

const attributeTypeDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>(
  'attributeTypeDropdownRef'
)

// On a fresh key with no type yet, auto-open the type dropdown. Deferred to
// nextTick so the `:disabled` gate has re-rendered and the inferred type has
// propagated before we read it.
watch(
  () => props.condition.key,
  (next, prev) => {
    if (next === prev || next === '') {
      return
    }
    void nextTick(() => {
      if (props.condition.attributeType !== null) {
        return
      }
      attributeTypeDropdownRef.value?.open()
    })
  }
)

const attributeTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'resource', title: _t('Resource') },
    { name: 'scope', title: _t('Scope') },
    { name: 'datapoint', title: _t('Data point') }
  ]
}))

function operatorSuggestion(name: Operator) {
  return { name, title: operatorPhrase(name) }
}

const operatorOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    {
      title: _t('Comparison'),
      suggestions: STRING_OPERATORS.map(operatorSuggestion)
    },
    {
      title: _t('Existence'),
      suggestions: EXISTENCE_OPERATORS.map(operatorSuggestion)
    }
  ]
}))
</script>

<template>
  <span
    class="metric-backend-attribute-filter-pill"
    :aria-label="ariaLabel ?? fullLabel"
    role="group"
  >
    <span class="metric-backend-attribute-filter-pill__segment" :title="fullLabel">
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-type"
      >
        <CmkDropdown
          ref="attributeTypeDropdownRef"
          v-model:selected-option="attributeTypeInput"
          :options="attributeTypeOptions"
          :disabled="!condition.key"
          :input-hint="_t('Attribute type')"
          :label="_t('Attribute type')"
          :required="!!condition.key"
          :form-validation="!!condition.key && !isPristine && attributeTypeEmpty"
        />
      </span>
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
      >
        <CmkDropdown
          :selected-option="condition.key || null"
          :options="{ type: 'callback-filtered', querySuggestions }"
          :label="_t('Attribute key')"
          :input-hint="_t('Attribute key')"
          required
          :form-validation="!isPristine && keyEmpty"
          @update:selected-option="onKeyUpdate"
        />
      </span>
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator"
      >
        <CmkDropdown
          :selected-option="condition.operator"
          :options="operatorOptions"
          :label="_t('Attribute operator')"
          @update:selected-option="onOperatorUpdate"
        />
      </span>
      <span
        v-if="showValue"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
      >
        <CmkDropdown
          ref="valueDropdownRef"
          :selected-option="condition.value || null"
          :options="valueOptions"
          :label="_t('Attribute value')"
          :input-hint="_t('Attribute value')"
          required
          :form-validation="!isPristine && valueEmpty"
          @update:selected-option="onValueUpdate"
        />
      </span>
    </span>
    <CmkIconButton
      v-if="removable"
      class="metric-backend-attribute-filter-pill__remove"
      name="close"
      size="small"
      :title="_t('Remove condition')"
      :aria-label="_t('Remove condition')"
      @mousedown.prevent
      @click.stop="emit('remove')"
    />
  </span>
</template>

<style scoped>
.metric-backend-attribute-filter-pill {
  display: inline-flex;
  align-items: stretch;
  background: var(--ux-theme-3);
  border: 1px solid var(--ux-theme-4);
  padding-right: var(--dimension-3);
  white-space: nowrap;
}

.metric-backend-attribute-filter-pill__segment {
  padding: var(--dimension-2) var(--dimension-3);
}

.metric-backend-attribute-filter-pill__remove {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
}
</style>
