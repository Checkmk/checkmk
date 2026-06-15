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
    tabFocusable?: boolean
  }>(),
  { removable: false, editing: false, tabFocusable: true }
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

const keyDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('keyDropdownRef')
const valueDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('valueDropdownRef')
const attributeTypeDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>(
  'attributeTypeDropdownRef'
)
const pendingValueOpen = ref(false)

const showValidationErrors = ref(false)

const validationVisible = computed(() => showValidationErrors.value)

const closedPillRef = useTemplateRef<HTMLElement>('closedPillRef')
let returnFocusToClosedPill = false

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

// Guided edit chain: each watcher auto-opens the next dropdown that still
// needs input, minimizing clicks on the common path.
watch(
  () => props.editing,
  (now) => {
    if (now) {
      armOutsideNextTask()
      if (!props.condition.key) {
        void nextTick(() => keyDropdownRef.value?.open())
      } else {
        void nextTick(() => attributeTypeDropdownRef.value?.focus())
      }
    } else {
      outsideArmed = false
      if (armTimer !== null) {
        clearTimeout(armTimer)
        armTimer = null
      }
      showValidationErrors.value = false
      if (returnFocusToClosedPill) {
        returnFocusToClosedPill = false
        void nextTick(() => closedPillRef.value?.focus())
      }
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

watch(
  () => props.condition.key,
  (next, prev) => {
    if (next === prev || next === '') {
      return
    }
    void nextTick(() => {
      if (props.condition.attributeType === null) {
        attributeTypeDropdownRef.value?.open()
        return
      }
      if (showValue.value && props.condition.value === '') {
        valueDropdownRef.value?.open()
      }
    })
  }
)

watch(
  () => props.condition.attributeType,
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

// Escape should close open Dropdown without commiting the pill
let escapeAteDropdown = false
function onEditEscapeCapture(): void {
  escapeAteDropdown =
    editPaneRef.value !== null && editPaneRef.value.querySelector('[aria-expanded="true"]') !== null
}
function onEditEscape(): void {
  if (escapeAteDropdown) {
    escapeAteDropdown = false
    return
  }
  if (hasValidationErrors.value) {
    showValidationErrors.value = true
    return
  }
  returnFocusToClosedPill = true
  emit('done')
}

defineExpose({
  revealValidationErrors: () => {
    showValidationErrors.value = true
  },
  focus: () => {
    closedPillRef.value?.focus()
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
      data-af-scope
      :title="fullLabel"
      @keydown.tab.capture.stop
      @keydown.esc.capture="onEditEscapeCapture"
      @keydown.esc.stop="onEditEscape"
    >
      <span
        v-if="condition.key"
        data-af-item
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
        data-af-item
        class="metric-backend-attribute-filter-pill__segment metric-backend-attribute-filter-pill__segment--key"
      >
        <CmkDropdown
          ref="keyDropdownRef"
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
        data-af-item
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
        data-af-item
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
      <CmkIconButton
        v-if="removable"
        data-af-item
        class="metric-backend-attribute-filter-pill__remove"
        name="close"
        size="small"
        :title="_t('Remove condition')"
        :aria-label="_t('Remove condition')"
        @mousedown.prevent
        @click.stop="emit('remove')"
      />
    </span>
    <span
      v-else
      ref="closedPillRef"
      data-af-item
      class="metric-backend-attribute-filter-pill__closed"
      :tabindex="tabFocusable ? 0 : -1"
      @keydown.enter.prevent="emit('edit')"
      @keydown.space.prevent="emit('edit')"
      @keydown.delete.prevent="emit('remove')"
    >
      <button
        type="button"
        class="metric-backend-attribute-filter-pill__main"
        tabindex="-1"
        :title="fullLabel"
        :aria-label="`${_t('Edit condition')}: ${fullLabel}`"
        @mousedown.prevent
        @click.stop="emit('edit')"
        @keydown.delete.prevent="emit('remove')"
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
        tabindex="-1"
        :title="_t('Remove condition')"
        :aria-label="_t('Remove condition')"
        @mousedown.prevent
        @click.stop="emit('remove')"
      />
    </span>
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

.metric-backend-attribute-filter-pill__closed {
  display: inline-flex;
  align-items: stretch;
}

.metric-backend-attribute-filter-pill__closed:focus-visible {
  outline: revert;
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
  background-color: var(--default-form-element-bg-color);
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

.metric-backend-attribute-filter-pill__remove:hover {
  background-color: var(--default-form-element-bg-color);
}
</style>
