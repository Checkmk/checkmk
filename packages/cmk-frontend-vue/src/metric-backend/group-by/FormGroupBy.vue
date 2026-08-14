<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import type {
  QuerySuggestionsFn,
  Suggestions
} from 'cmk-ui-library/components/CmkSuggestions/types'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { attributeKindLabel } from '../attribute-kind'
import { DEFAULT_QUANTILE, useHistogramParams } from '../histogram-params'
import GroupByKeyPill from './GroupByKeyPill.vue'
import { clauseSummary, compactFunctionLabel, functionLabel } from './group-by-label'
import {
  defaultFunction,
  functionParamKind,
  functionTakesKeys,
  functionsForInputType,
  isFunctionValidForInputType,
  isKeyValid
} from './types'
import type {
  AttributeKind,
  GroupByFunction,
  GroupByInputType,
  GroupByModel,
  GroupKey,
  ParamKind
} from './types'

const { _t } = usei18n()

const props = defineProps<{
  // The consolidation output type for the same graph line.
  inputType: GroupByInputType
  querySuggestions: QuerySuggestionsFn
  resolveAttributeKind?: ((key: string) => AttributeKind | null) | undefined
  ariaLabel?: string | undefined
}>()

const model = defineModel<GroupByModel>({ required: true })

const summary = computed(() => clauseSummary(model.value))
const editAriaLabel = computed(() => `${_t('Edit group by')}: ${summary.value}`)

const functionOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: functionsForInputType(props.inputType).map((fn) => ({
    name: fn,
    title: functionLabel(fn)
  }))
}))

function applyFunction(fn: GroupByFunction): void {
  // Drop the previous function's params, seeding the quantile default so its field isn't blank.
  const params = functionParamKind(fn) === 'quantile' ? { quantile: DEFAULT_QUANTILE } : {}
  model.value = { ...model.value, function: fn, params }
}

function onFunctionUpdate(value: string | null): void {
  if (value === null) {
    return
  }
  applyFunction(value as GroupByFunction)
}

// A new output type may no longer offer the current function; reset to its default.
watch(
  () => props.inputType,
  (type) => {
    if (!isFunctionValidForInputType(type, model.value.function)) {
      applyFunction(defaultFunction(type))
    }
  }
)

const paramKind = computed<ParamKind>(() => functionParamKind(model.value.function))

// "No grouping" takes no keys: the keys area is hidden, though the model keeps them.
const keysEnabled = computed(() => functionTakesKeys(model.value.function))

function setParam(key: keyof GroupByModel['params'], value: number | undefined): void {
  model.value = { ...model.value, params: { ...model.value.params, [key]: value } }
}

const {
  quantileInput,
  fractionBelowThresholdInput,
  fractionLowerThresholdInput,
  fractionUpperThresholdInput,
  quantileErrors,
  fractionBelowThresholdErrors,
  fractionBetweenErrors
} = useHistogramParams(() => model.value.params, setParam)

const activeErrors = computed<string[]>(() => {
  switch (paramKind.value) {
    case 'quantile':
      return quantileErrors.value
    case 'fraction_below':
      return fractionBelowThresholdErrors.value
    case 'fraction_between':
      return fractionBetweenErrors.value
    default:
      return []
  }
})

const editing = ref(false)

// Hide param errors until the user tries to leave with an invalid one (see canLeaveEdit).
const showValidationErrors = ref(false)

const validationMessages = computed<string[]>(() =>
  showValidationErrors.value ? activeErrors.value : []
)

const functionDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('functionDropdownRef')

const editingId = ref<string | null>(null)

function onEdit(): void {
  editing.value = true
  showValidationErrors.value = false
  void nextTick(() => {
    // "No grouping" has nothing else to edit: open the function dropdown directly.
    if (model.value.function === 'none') {
      functionDropdownRef.value?.open()
      return
    }
    // A lone key is the obvious target; open it directly.
    if (model.value.keys.length === 1) {
      editingId.value = model.value.keys[0]!.id
      return
    }
    functionDropdownRef.value?.focus()
  })
}

const pillRefs = new Map<string, InstanceType<typeof GroupByKeyPill>>()

// Cache one setter per pill id so :ref does not see a new function every render
// and re-run the setter on every model mutation.
const pillRefSetters = new Map<string, (el: unknown) => void>()
function pillRefSetter(id: string): (el: unknown) => void {
  let fn = pillRefSetters.get(id)
  if (!fn) {
    fn = (el: unknown) => {
      if (el) {
        pillRefs.set(id, el as InstanceType<typeof GroupByKeyPill>)
      } else {
        pillRefs.delete(id)
        pillRefSetters.delete(id)
      }
    }
    pillRefSetters.set(id, fn)
  }
  return fn
}

function tryChangeFocus(): boolean {
  const id = editingId.value
  if (id === null) {
    return true
  }
  const key = model.value.keys.find((k) => k.id === id)
  if (!key || isKeyValid(key)) {
    return true
  }
  pillRefs.get(id)?.revealValidationErrors()
  return false
}

function addKey(): void {
  if (!keysEnabled.value || !tryChangeFocus()) {
    return
  }
  const fresh: GroupKey = { id: randomId(), attributeKind: null, attributeKey: '' }
  model.value = { ...model.value, keys: [...model.value.keys, fresh] }
  editingId.value = fresh.id
}

function removeKey(target: GroupKey): void {
  if (editingId.value === target.id) {
    editingId.value = null
  }
  model.value = { ...model.value, keys: model.value.keys.filter((k) => k.id !== target.id) }
}

function mapKeys(fn: (key: GroupKey) => GroupKey): void {
  model.value = { ...model.value, keys: model.value.keys.map(fn) }
}

function updateAttributeKind(target: GroupKey, value: AttributeKind): void {
  mapKeys((k) => (k.id === target.id ? { ...k, attributeKind: value } : k))
}

// Override the kind only when the key resolves, so a user-picked kind survives free-text edits.
function updateAttributeKey(target: GroupKey, value: string): void {
  const inferred = value !== '' ? (props.resolveAttributeKind?.(value) ?? null) : null
  mapKeys((k) =>
    k.id === target.id
      ? { ...k, attributeKey: value, ...(inferred !== null ? { attributeKind: inferred } : {}) }
      : k
  )
}

function startEditing(id: string): void {
  if (!tryChangeFocus()) {
    return
  }
  editingId.value = id
}

function onKeyEditDone(id: string): void {
  if (editingId.value === id) {
    editingId.value = null
  }
}

// Veto closing while a param is invalid or a pending key is empty, revealing the error.
function canLeaveEdit(): boolean {
  if (activeErrors.value.length > 0) {
    showValidationErrors.value = true
    return false
  }
  return tryChangeFocus()
}
</script>

<template>
  <div class="metric-backend-form-group-by">
    <CmkInlineValidation :validation="validationMessages" />
    <InlineEditPill
      :editing="editing"
      :tab-focusable="false"
      :can-leave="canLeaveEdit"
      :aria-label="ariaLabel ?? summary"
      :edit-aria-label="editAriaLabel"
      scope-marker-attr="data-gb-scope"
      item-marker-attr="data-gb-item"
      @edit="onEdit"
      @done="editing = false"
    >
      <template #read-only>
        <span class="metric-backend-form-group-by__summary">
          <span class="metric-backend-form-group-by__segment">{{
            compactFunctionLabel(model)
          }}</span>
          <template v-if="keysEnabled">
            <span v-if="model.keys.length === 0" class="metric-backend-form-group-by__everything">{{
              _t('everything')
            }}</span>
            <template v-for="(key, index) in model.keys" :key="key.id">
              <span
                v-if="key.attributeKind !== null"
                class="metric-backend-form-group-by__segment metric-backend-form-group-by__segment--dimmed"
                >[{{ attributeKindLabel(key.attributeKind) }}]</span
              >
              <!-- Comma hugs the key; the segment's own right padding spaces it from the next term. -->
              <span class="metric-backend-form-group-by__segment"
                >{{ key.attributeKey }}{{ index < model.keys.length - 1 ? ',' : '' }}</span
              >
            </template>
          </template>
        </span>
      </template>
      <template #edit>
        <span class="metric-backend-form-group-by__segment">
          <CmkDropdown
            ref="functionDropdownRef"
            floating
            :model-value="model.function"
            :options="functionOptions"
            :label="_t('Grouping function')"
            @update:model-value="onFunctionUpdate"
          />
        </span>
        <span v-if="paramKind === 'quantile'" class="metric-backend-form-group-by__param">
          <CmkInput
            v-model="quantileInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? quantileErrors : []"
            hide-validation-message
            :aria-label="_t('Quantile (0 to 1)')"
            :placeholder="_t('Quantile')"
          />
        </span>
        <span v-if="paramKind === 'fraction_below'" class="metric-backend-form-group-by__param">
          <CmkInput
            v-model="fractionBelowThresholdInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? fractionBelowThresholdErrors : []"
            hide-validation-message
            :aria-label="_t('Threshold')"
            :placeholder="_t('Threshold')"
          />
        </span>
        <span v-if="paramKind === 'fraction_between'" class="metric-backend-form-group-by__param">
          <CmkInput
            v-model="fractionLowerThresholdInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? fractionBetweenErrors : []"
            hide-validation-message
            :aria-label="_t('Lower threshold')"
            :placeholder="_t('Lower')"
          />
          <span class="metric-backend-form-group-by__word">–</span>
          <CmkInput
            v-model="fractionUpperThresholdInput"
            type="number"
            inline
            :aria-label="_t('Upper threshold')"
            :placeholder="_t('Upper')"
          />
        </span>
        <div
          v-if="keysEnabled"
          class="metric-backend-form-group-by__keys"
          data-testid="group-by-keys"
        >
          <span v-if="model.keys.length === 0" class="metric-backend-form-group-by__everything">{{
            _t('everything')
          }}</span>
          <GroupByKeyPill
            v-for="key in model.keys"
            :key="key.id"
            :ref="pillRefSetter(key.id)"
            :condition="key"
            :query-suggestions="querySuggestions"
            removable
            :editing="key.id === editingId"
            @remove="removeKey(key)"
            @edit="startEditing(key.id)"
            @done="onKeyEditDone(key.id)"
            @update:attribute-kind="(value) => updateAttributeKind(key, value)"
            @update:attribute-key="(value) => updateAttributeKey(key, value)"
          />
          <CmkIconButton
            class="metric-backend-form-group-by__add"
            name="add"
            size="large"
            :title="_t('Add group key')"
            :aria-label="_t('Add group key')"
            @mousedown.prevent
            @click="addKey"
          />
        </div>
      </template>
    </InlineEditPill>
  </div>
</template>

<style scoped>
.metric-backend-form-group-by {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-2);
}

.metric-backend-form-group-by__summary {
  display: inline-flex;
  align-items: center;
}

.metric-backend-form-group-by__segment {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}

.metric-backend-form-group-by__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-form-group-by__param {
  display: inline-flex;
  align-items: center;
  padding-left: var(--dimension-2);
}

/* Widen the narrow default number field so the placeholder fits. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.metric-backend-form-group-by__param :deep(.cmk-input--number) {
  width: 6em;
}

.metric-backend-form-group-by__word {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.metric-backend-form-group-by__keys {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3) var(--dimension-4);
  padding-left: var(--dimension-2);
}

.metric-backend-form-group-by__everything {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-form-group-by__add:hover {
  background-color: var(--input-hover-bg-color);
}
</style>
