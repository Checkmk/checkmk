<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'

import usei18n from '@/lib/i18n'
import useClickOutside from '@/lib/useClickOutside'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import type { QuerySuggestionsFn } from '@/components/CmkSuggestions/types'

import { ATTRIBUTE_TYPE_LABELS, attributeTypePrefix, operatorPhrase, pillLabel } from './pill-label'
import {
  EXISTENCE_OPERATORS,
  STRING_OPERATORS,
  isConditionValid,
  isOperator,
  operatorTakesValue
} from './types'
import type { AttributeCondition, AttributeType, Operator } from './types'

const { _t } = usei18n()

const vClickOutside = useClickOutside()

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
    editing?: boolean
  }>(),
  { removable: false, editing: false }
)

const emit = defineEmits<{
  (e: 'remove'): void
  (e: 'edit'): void
  (e: 'done'): void
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

const valueDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('valueDropdownRef')
const pendingValueOpen = ref(false)

const showValidationErrors = ref(false)

const validationVisible = computed(() => showValidationErrors.value)

// The click that creates a pill in edit mode keeps bubbling after Vue mounts
// the new edit branch. Defer arming the outside-click handler by one task so
// that tail bubble does not turn into the pill's own first commit attempt.
let outsideArmed = false
let armTimer: ReturnType<typeof setTimeout> | null = null
function armOutsideNextTask(): void {
  if (armTimer !== null) {
    clearTimeout(armTimer)
  }
  armTimer = setTimeout(() => {
    outsideArmed = true
    armTimer = null
  }, 0)
}
watch(
  () => props.editing,
  (now) => {
    if (now) {
      armOutsideNextTask()
    } else {
      outsideArmed = false
      if (armTimer !== null) {
        clearTimeout(armTimer)
        armTimer = null
      }
      showValidationErrors.value = false
    }
  },
  { immediate: true }
)

const attributeTypeText = computed(() => attributeTypePrefix(props.condition.attributeType).trim())
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

const attributeTypeInput = computed<string | null>({
  get: () => props.condition.attributeType,
  set: (value) => {
    const valid =
      value !== null && Object.hasOwn(ATTRIBUTE_TYPE_LABELS, value)
        ? (value as AttributeType)
        : null
    emit('update:attributeType', valid)
  }
})

const attributeTypeDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>(
  'attributeTypeDropdownRef'
)

// On a fresh key with no type yet, auto-open the type dropdown. Deferred to
// nextTick so the `v-if` gate has mounted the dropdown and the inferred type
// has propagated before we read it.
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

const hasValidationErrors = computed(() => !isConditionValid(props.condition))

const editPaneRef = useTemplateRef<HTMLElement>('editPaneRef')

// Prevent a click inside the edit pane from counting as outside and commiting the pill.
let mousedownInside = false
function onBodyMousedown(event: MouseEvent): void {
  const target = event.target
  mousedownInside =
    editPaneRef.value !== null && target instanceof Node && editPaneRef.value.contains(target)
}
onMounted(() => {
  document.addEventListener('mousedown', onBodyMousedown, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onBodyMousedown, true)
})

function onOutside(): void {
  if (mousedownInside) {
    mousedownInside = false
    return
  }
  if (!outsideArmed) {
    return
  }
  if (hasValidationErrors.value) {
    showValidationErrors.value = true
    return
  }
  emit('done')
}

defineExpose({
  revealValidationErrors: () => {
    showValidationErrors.value = true
  }
})
</script>

<template>
  <span
    class="metric-backend-attribute-filter-pill"
    :aria-label="ariaLabel ?? fullLabel"
    role="group"
  >
    <span
      v-if="editing"
      ref="editPaneRef"
      v-click-outside="onOutside"
      class="metric-backend-attribute-filter-pill__edit"
      :title="fullLabel"
    >
      <span
        v-if="condition.key"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-type"
      >
        <CmkDropdown
          ref="attributeTypeDropdownRef"
          v-model="attributeTypeInput"
          :options="attributeTypeOptions"
          :input-hint="_t('Attribute type')"
          :label="_t('Attribute type')"
          :required="validationVisible"
          :form-validation="validationVisible && attributeTypeEmpty"
        />
      </span>
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
      >
        <CmkDropdown
          :model-value="condition.key || null"
          :options="{ type: 'callback-filtered', querySuggestions }"
          :label="_t('Attribute key')"
          :input-hint="_t('Attribute key')"
          :required="validationVisible"
          :form-validation="validationVisible && keyEmpty"
          @update:model-value="onKeyUpdate"
        />
      </span>
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator"
      >
        <CmkDropdown
          :model-value="condition.operator"
          :options="operatorOptions"
          :label="_t('Attribute operator')"
          @update:model-value="onOperatorUpdate"
        />
      </span>
      <span
        v-if="showValue"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
      >
        <CmkDropdown
          ref="valueDropdownRef"
          :model-value="condition.value || null"
          :options="valueOptions"
          :label="_t('Attribute value')"
          :input-hint="_t('Attribute value')"
          :required="validationVisible"
          :form-validation="validationVisible && valueEmpty"
          @update:model-value="onValueUpdate"
        />
      </span>
    </span>
    <button
      v-else
      type="button"
      class="metric-backend-attribute-filter-pill__main"
      :title="fullLabel"
      :aria-label="`${_t('Edit condition')}: ${fullLabel}`"
      @mousedown.prevent
      @click.stop="emit('edit')"
    >
      <span
        v-if="attributeTypeText !== ''"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--attribute-type"
        >{{ attributeTypeText }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
        >{{ condition.key }}</span
      >
      <span
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--operator"
        >{{ operatorText }}</span
      >
      <span
        v-if="showValue"
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--value"
        >{{ condition.value }}</span
      >
    </button>
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

.metric-backend-attribute-filter-pill__edit {
  display: inline-flex;
}

.metric-backend-attribute-filter-pill__main {
  display: inline-flex;
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.metric-backend-attribute-filter-pill__main:hover {
  background: var(--ux-theme-4);
}

.metric-backend-attribute-filter-pill__main:focus-visible {
  outline: revert;
}

.metric-backend-attribute-filter-pill__segment {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}

.metric-backend-attribute-filter-pill__main
  .metric-backend-attribute-filter-pill__segment--attribute-type,
.metric-backend-attribute-filter-pill__main
  .metric-backend-attribute-filter-pill__segment--operator {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-attribute-filter-pill__remove {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
}
</style>
