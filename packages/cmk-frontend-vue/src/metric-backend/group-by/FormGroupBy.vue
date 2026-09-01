<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type {
  QuerySuggestionsFn,
  Suggestions
} from 'cmk-ui-library/components/CmkSuggestions/types'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { attributeKindLabel } from '../attribute-kind'
import { DEFAULT_QUANTILE, useHistogramParams } from '../histogram-params'
import GroupByKeysArea from './GroupByKeysArea.vue'
import { clauseSummary, compactFunctionLabel, functionLabel } from './group-by-label'
import {
  defaultFunction,
  functionParamKind,
  functionTakesKeys,
  functionsForInputType,
  isFunctionValidForInputType
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

const props = withDefaults(
  defineProps<{
    // The consolidation output type for the same graph line.
    inputType: GroupByInputType
    querySuggestions: QuerySuggestionsFn
    suggestionRevision?: number
    resolveAttributeKind?: ((key: string) => AttributeKind | null) | undefined
    ariaLabel?: string | undefined
  }>(),
  { suggestionRevision: 0 }
)

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

function removeGrouping(): void {
  applyFunction('none')
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
const keysAreaRef = useTemplateRef<InstanceType<typeof GroupByKeysArea>>('keysAreaRef')

const keysModel = computed<GroupKey[]>({
  get: () => model.value.keys,
  set: (keys) => {
    model.value = { ...model.value, keys }
  }
})

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
      keysAreaRef.value?.focusKey(model.value.keys[0]!.id)
      return
    }
    functionDropdownRef.value?.focus()
  })
}

// Veto closing while a param is invalid or a pending key is empty, revealing the error.
function canLeaveEdit(): boolean {
  if (activeErrors.value.length > 0) {
    showValidationErrors.value = true
    return false
  }
  return keysAreaRef.value?.tryChangeFocus() ?? true
}
</script>

<template>
  <div class="metric-backend-form-group-by">
    <CmkInlineValidation :validation="validationMessages" />
    <InlineEditPill
      :editing="editing"
      :removable="model.function !== 'none' && !editing"
      :can-leave="canLeaveEdit"
      :aria-label="ariaLabel ?? summary"
      :edit-aria-label="editAriaLabel"
      :remove-label="_t('Remove grouping')"
      scope-marker-attr="data-gb-scope"
      item-marker-attr="data-gb-item"
      @edit="onEdit"
      @done="editing = false"
      @remove="removeGrouping"
    >
      <template #read-only>
        <span class="metric-backend-form-group-by__summary">
          <span class="metric-backend-form-group-by__segment">{{
            compactFunctionLabel(model)
          }}</span>
          <template v-if="keysEnabled">
            <span v-if="model.keys.length === 0" class="metric-backend-form-group-by__everything">{{
              _t('nothing, combine all series into one')
            }}</span>
            <template v-for="(key, index) in model.keys" :key="key.id">
              <span
                v-if="key.attributeKind !== null"
                class="metric-backend-form-group-by__segment metric-backend-form-group-by__segment--dimmed"
                >[{{ attributeKindLabel(key.attributeKind) }}]</span
              >
              <!-- Comma stays glued to the key so the summary gap only spaces whole terms. -->
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
        <GroupByKeysArea
          v-if="keysEnabled"
          ref="keysAreaRef"
          v-model="keysModel"
          :query-suggestions="querySuggestions"
          :suggestion-revision="suggestionRevision"
          :resolve-attribute-kind="resolveAttributeKind"
          testid="group-by-keys"
        />
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
  gap: var(--dimension-4);
}

.metric-backend-form-group-by__segment {
  padding: var(--dimension-2) 0;
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
  gap: var(--dimension-2);
}

/* Widen the narrow default number field so the placeholder fits. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.metric-backend-form-group-by__param :deep(.cmk-input--number) {
  width: 6em;
}

.metric-backend-form-group-by__word {
  display: inline-flex;
  align-items: center;
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.metric-backend-form-group-by__everything {
  color: var(--font-color-dimmed);
  font-style: italic;
}
</style>
