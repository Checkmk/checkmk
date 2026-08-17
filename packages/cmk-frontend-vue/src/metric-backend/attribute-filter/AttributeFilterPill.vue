<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import DropdownClearButton from '../DropdownClearButton.vue'
import InlineEditPill from '../InlineEditPill.vue'
import { ATTRIBUTE_KIND_ORDER, attributeKindLabel } from '../attribute-kind'
import { attributeKindPrefix, operatorPhrase, pillLabel } from './pill-label'
import {
  EXISTENCE_OPERATORS,
  STRING_OPERATORS,
  isConditionValid,
  isOperator,
  operatorTakesValue
} from './types'
import type { AttributeKind, Condition, Operator } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    condition: Condition
    querySuggestions: (condition: Condition, query: string) => ReturnType<QuerySuggestionsFn>
    queryValueSuggestions: (condition: Condition, query: string) => ReturnType<QuerySuggestionsFn>
    suggestionRevision?: number
    operators?: Operator[] | undefined
    ariaLabel?: string | undefined
    removable?: boolean
    editing?: boolean
    tabFocusable?: boolean
  }>(),
  {
    suggestionRevision: 0,
    operators: () => [...STRING_OPERATORS, ...EXISTENCE_OPERATORS],
    removable: false,
    editing: false,
    tabFocusable: true
  }
)

// A single allowed operator is fixed: the dropdown would offer no choice, so hide it.
const showOperator = computed(() => props.operators.length > 1)

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'edit'): void
  (e: 'done'): void
  (e: 'update:key', value: string): void
  (e: 'update:attributeKind', value: AttributeKind | null): void
  (e: 'update:operator', value: Operator): void
  (e: 'update:value', value: string): void
}>()

const fullLabel = computed(() => pillLabel(props.condition))
const showValue = computed(() => operatorTakesValue(props.condition.operator))

// Reading the revision yields a fresh options identity on each bump, so CmkSuggestions re-queries.
const keyOptions = computed(() => {
  void props.suggestionRevision
  return {
    type: 'callback-filtered' as const,
    querySuggestions: (query: string) => props.querySuggestions(props.condition, query)
  }
})
const valueOptions = computed(() => {
  void props.suggestionRevision
  return {
    type: 'callback-filtered' as const,
    querySuggestions: (query: string) => props.queryValueSuggestions(props.condition, query)
  }
})

const attributeKindEmpty = computed(() => props.condition.attributeKind === null)
const keyEmpty = computed(() => !props.condition.key)
const valueEmpty = computed(() => props.condition.value === '')

const keyDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('keyDropdownRef')
const valueDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('valueDropdownRef')
const attributeKindDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>(
  'attributeKindDropdownRef'
)
const pendingValueOpen = ref(false)

const showValidationErrors = ref(false)

const validationVisible = computed(() => showValidationErrors.value)

const pillRef = useTemplateRef<InstanceType<typeof InlineEditPill>>('pillRef')

// Guided edit chain: each watcher auto-opens the next dropdown that still
// needs input, minimizing clicks on the common path.
watch(
  () => props.editing,
  (now) => {
    if (now) {
      if (!props.condition.key) {
        void nextTick(() => keyDropdownRef.value?.open())
      } else {
        void nextTick(() => attributeKindDropdownRef.value?.focus())
      }
    } else {
      showValidationErrors.value = false
    }
  },
  { immediate: true }
)

const attributeKindText = computed(() => attributeKindPrefix(props.condition.attributeKind).trim())
const operatorText = computed(() => operatorPhrase(props.condition.operator))

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

const attributeKindInput = computed<string | null>({
  get: () => props.condition.attributeKind,
  set: (value) => {
    const valid =
      value !== null && (ATTRIBUTE_KIND_ORDER as string[]).includes(value)
        ? (value as AttributeKind)
        : null
    emit('update:attributeKind', valid)
  }
})

// Clearing unmounts the clear button, so reopen the dropdown: focus returns to the
// field and its suggestions expand so a new value can be picked right away.
function clearKey(): void {
  onKeyUpdate(null)
  void nextTick(() => keyDropdownRef.value?.open())
}

function clearValue(): void {
  onValueUpdate(null)
  void nextTick(() => valueDropdownRef.value?.open())
}

watch(
  () => props.condition.key,
  (next, prev) => {
    if (next === prev || next === '') {
      return
    }
    void nextTick(() => {
      if (props.condition.attributeKind === null) {
        attributeKindDropdownRef.value?.open()
        return
      }
      if (showValue.value && props.condition.value === '') {
        valueDropdownRef.value?.open()
      }
    })
  }
)

watch(
  () => props.condition.attributeKind,
  (next, prev) => {
    if (
      !props.editing ||
      next === null ||
      prev !== null ||
      !props.condition.key ||
      !showValue.value ||
      props.condition.value !== ''
    ) {
      return
    }
    void nextTick(() => valueDropdownRef.value?.open())
  }
)

const attributeKindOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: ATTRIBUTE_KIND_ORDER.map((attributeKind) => ({
    name: attributeKind,
    title: attributeKindLabel(attributeKind)
  }))
}))

function operatorSuggestion(name: Operator) {
  return { name, title: operatorPhrase(name) }
}

const operatorOptions = computed(() => {
  const comparison = STRING_OPERATORS.filter((op) => props.operators.includes(op))
  const existence = EXISTENCE_OPERATORS.filter((op) => props.operators.includes(op))
  const sections = []
  if (comparison.length > 0) {
    sections.push({ title: _t('Comparison'), suggestions: comparison.map(operatorSuggestion) })
  }
  if (existence.length > 0) {
    sections.push({ title: _t('Existence'), suggestions: existence.map(operatorSuggestion) })
  }
  return { type: 'fixed' as const, suggestions: sections }
})

const hasValidationErrors = computed(() => !isConditionValid(props.condition))

// Veto committing the pill while a required field is still empty: reveal the
// errors and keep editing. The pill handles emitting `done` and the focus
// return when leaving is allowed.
function canLeave(): boolean {
  if (hasValidationErrors.value) {
    showValidationErrors.value = true
    return false
  }
  return true
}

defineExpose({
  revealValidationErrors: () => {
    showValidationErrors.value = true
  },
  focus: () => {
    pillRef.value?.focus()
  }
})
</script>

<template>
  <InlineEditPill
    ref="pillRef"
    :editing="editing"
    :removable="removable"
    :tab-focusable="tabFocusable"
    :aria-label="ariaLabel ?? fullLabel"
    :title="fullLabel"
    :edit-aria-label="`${_t('Edit condition')}: ${fullLabel}`"
    :remove-label="_t('Remove condition')"
    :can-leave="canLeave"
    scope-marker-attr="data-af-scope"
    item-marker-attr="data-af-item"
    @edit="emit('edit')"
    @remove="emit('remove')"
    @done="emit('done')"
  >
    <template #edit>
      <span
        v-if="condition.key"
        data-af-item
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-kind"
      >
        <CmkDropdown
          ref="attributeKindDropdownRef"
          v-model="attributeKindInput"
          floating
          :options="attributeKindOptions"
          :input-hint="_t('Attribute kind')"
          :label="_t('Attribute kind')"
          :required="validationVisible"
          :form-validation="validationVisible && attributeKindEmpty"
        />
      </span>
      <span
        data-af-item
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
      >
        <CmkDropdown
          ref="keyDropdownRef"
          floating
          :model-value="condition.key || null"
          :options="keyOptions"
          :label="_t('Attribute key')"
          :input-hint="_t('Attribute key')"
          :required="validationVisible"
          :form-validation="validationVisible && keyEmpty"
          @update:model-value="onKeyUpdate"
        >
          <template v-if="!keyEmpty" #buttons-end>
            <DropdownClearButton data-af-item @clear="clearKey" />
          </template>
        </CmkDropdown>
      </span>
      <span
        v-if="showOperator"
        data-af-item
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator"
      >
        <CmkDropdown
          floating
          :model-value="condition.operator"
          :options="operatorOptions"
          :label="_t('Attribute operator')"
          @update:model-value="onOperatorUpdate"
        />
      </span>
      <span
        v-else
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator metric-backend-attribute-filter-pill__segment--dimmed"
        >{{ operatorText }}</span
      >
      <span
        v-if="showValue"
        data-af-item
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
      >
        <CmkDropdown
          ref="valueDropdownRef"
          floating
          :model-value="condition.value || null"
          :options="valueOptions"
          :label="_t('Attribute value')"
          :input-hint="_t('Attribute value')"
          :required="validationVisible"
          :form-validation="validationVisible && valueEmpty"
          @update:model-value="onValueUpdate"
        >
          <template v-if="!valueEmpty" #buttons-end>
            <DropdownClearButton data-af-item @clear="clearValue" />
          </template>
        </CmkDropdown>
      </span>
    </template>
    <template #read-only>
      <span
        v-if="attributeKindText !== ''"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-kind metric-backend-attribute-filter-pill__segment--dimmed"
        >{{ attributeKindText }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
        >{{ condition.key }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator metric-backend-attribute-filter-pill__segment--dimmed"
        >{{ operatorText }}</span
      >
      <span
        v-if="showValue"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
        >{{ condition.value }}</span
      >
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-attribute-filter-pill__segment {
  padding: var(--dimension-2) 0;
  display: inline-flex;
  align-items: center;
}

.metric-backend-attribute-filter-pill__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
