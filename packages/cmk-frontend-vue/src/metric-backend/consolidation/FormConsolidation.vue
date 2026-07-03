<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import type { Section, Suggestions } from '@/components/CmkSuggestions/types'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'

import InlineEditPill from '../InlineEditPill.vue'
import {
  compactFunction,
  functionOptionLabel,
  lookbackLabel,
  typeLabel
} from './consolidation-label'
import { CONSOLIDATION_CATALOG, DEFAULT_QUANTILE, METRIC_TYPES, defaultFunction } from './types'
import type {
  ConsolidationFunction,
  ConsolidationModel,
  ConsolidationParams,
  MetricType
} from './types'

const { _t } = usei18n()

const props = defineProps<{
  // The metric types the backend resolved for the current metric.
  // An empty list results in every type's functions to be offered.
  availableTypes: MetricType[]
}>()

const model = defineModel<ConsolidationModel>({ required: true })

const typeToken = computed(() => `[${model.value.type}]`)
const functionToken = computed(() => compactFunction(model.value))
const lookbackToken = computed(() => lookbackLabel(model.value.lookbackSeconds))

const candidateTypes = computed<MetricType[]>(() =>
  props.availableTypes.length > 0 ? props.availableTypes : [...METRIC_TYPES]
)

function suggestionsForType(type: MetricType) {
  return CONSOLIDATION_CATALOG[type].map((spec) => ({
    name: `${type}:${spec.fn}`,
    title: functionOptionLabel(type, spec.fn, spec.raw)
  }))
}

const functionOptions = computed<Suggestions>(() => {
  // More than one candidate type is ambiguous: group per type so the choice also fixes it.
  if (candidateTypes.value.length > 1) {
    const sections: Section[] = candidateTypes.value.map((type) => ({
      title: _t('Treat as %{type}', { type: typeLabel(type) }),
      suggestions: suggestionsForType(type)
    }))
    return { type: 'fixed', suggestions: sections }
  }
  return { type: 'fixed', suggestions: suggestionsForType(candidateTypes.value[0]!) }
})

const dropdownValue = computed(() => `${model.value.type}:${model.value.function}`)

function applyFunction(type: MetricType, fn: ConsolidationFunction): void {
  // Reset params; they belonged to the previous function. Seed the quantile
  // default so its field isn't blank the moment the function is picked.
  const params: ConsolidationParams = fn === 'quantile' ? { quantile: DEFAULT_QUANTILE } : {}
  model.value = { ...model.value, type, function: fn, params }
}

function onFunctionUpdate(value: string | null): void {
  if (value === null) {
    return
  }
  const [type, fn] = value.split(':') as [MetricType, ConsolidationFunction]
  applyFunction(type, fn)
}

watch(candidateTypes, (types) => {
  if (types.includes(model.value.type)) {
    return
  }
  const type = types[0]!
  applyFunction(type, defaultFunction(type))
})

const editing = ref(false)

// Keep required-field errors hidden while the user is still filling the pill in;
// only reveal them once they try to leave with an invalid param (see canLeaveEdit).
const showValidationErrors = ref(false)

const functionDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('functionDropdownRef')

function onEdit(): void {
  editing.value = true
  showValidationErrors.value = false
  void nextTick(() => functionDropdownRef.value?.focus())
}

const lookbackInput = computed<number | null>({
  get: () => model.value.lookbackSeconds,
  set: (value) => {
    model.value = {
      ...model.value,
      lookbackSeconds: value ?? model.value.lookbackSeconds
    }
  }
})

function setParam(key: keyof ConsolidationModel['params'], value: number | undefined): void {
  model.value = { ...model.value, params: { ...model.value.params, [key]: value } }
}

// An emptied number input surfaces as NaN (not undefined); fold every non-finite
// value to undefined so a blank field never lands as NaN in the model, where it
// would trip the range/order checks and render as "pNaN" in the chip.
function normalizeNumber(value: number | undefined): number | undefined {
  return Number.isFinite(value) ? value : undefined
}

const quantileInput = computed<number | undefined>({
  get: () => model.value.params.quantile,
  set: (value) => setParam('quantile', normalizeNumber(value))
})

function quantileInRange(value: number): boolean {
  return value >= 0 && value <= 1
}

// A value is required, so a blank field fails; a set value must be in range.
const quantileErrors = computed<string[]>(() => {
  const { quantile } = model.value.params
  return quantile !== undefined && quantileInRange(quantile)
    ? []
    : [_t('Enter a quantile between 0 and 1')]
})

const fractionBelowThresholdInput = computed<number | undefined>({
  get: () => model.value.params.fractionBelowThreshold,
  set: (value) => setParam('fractionBelowThreshold', normalizeNumber(value))
})

// A threshold is required, so a blank field fails.
const fractionBelowThresholdErrors = computed<string[]>(() =>
  model.value.params.fractionBelowThreshold === undefined ? [_t('Enter a threshold')] : []
)

const fractionLowerThresholdInput = computed<number | undefined>({
  get: () => model.value.params.fractionLowerThreshold,
  set: (value) => setParam('fractionLowerThreshold', normalizeNumber(value))
})

const fractionUpperThresholdInput = computed<number | undefined>({
  get: () => model.value.params.fractionUpperThreshold,
  set: (value) => setParam('fractionUpperThreshold', normalizeNumber(value))
})

// Cross-field, so it's computed here; a per-input validator would miss the other bound's changes.
const fractionBetweenErrors = computed<string[]>(() => {
  const { fractionLowerThreshold, fractionUpperThreshold } = model.value.params
  if (fractionLowerThreshold === undefined || fractionUpperThreshold === undefined) {
    return [_t('Enter both thresholds')]
  }
  return fractionLowerThreshold < fractionUpperThreshold
    ? []
    : [_t('Lower threshold must be below the upper threshold')]
})

const activeErrors = computed<string[]>(() => {
  switch (model.value.function) {
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

// Veto closing while the active function's param is invalid (which includes a
// blank required field), revealing the error the first time leaving is blocked.
function canLeaveEdit(): boolean {
  if (activeErrors.value.length > 0) {
    showValidationErrors.value = true
    return false
  }
  return true
}

const editAriaLabel = computed(
  () =>
    `${_t('Edit consolidation')}: ${typeToken.value} ${functionToken.value} ${lookbackToken.value}`
)
</script>

<template>
  <InlineEditPill
    :editing="editing"
    :tab-focusable="false"
    :can-leave="canLeaveEdit"
    :edit-aria-label="editAriaLabel"
    scope-marker-attr="data-consolidation-scope"
    item-marker-attr="data-consolidation-item"
    @edit="onEdit"
    @done="editing = false"
  >
    <template #read-only>
      <span
        class="metric-backend-form-consolidation__segment metric-backend-form-consolidation__segment--dimmed"
        >{{ typeToken }}</span
      >
      <span class="metric-backend-form-consolidation__segment">{{ functionToken }}</span>
      <!-- Collapsed view stays terse: a middle dot stands in for the "over last"
      the edit mode spells out in full. -->
      <span class="metric-backend-form-consolidation__word" aria-hidden="true">·</span>
      <span class="metric-backend-form-consolidation__segment">{{ lookbackToken }}</span>
    </template>
    <template #edit>
      <!--
      Mirror the read-only summary for not yet as editable implemented elements
      -->
      <span
        class="metric-backend-form-consolidation__segment metric-backend-form-consolidation__segment--dimmed"
        >{{ typeToken }}</span
      >
      <CmkDropdown
        ref="functionDropdownRef"
        :selected-option="dropdownValue"
        :options="functionOptions"
        :label="_t('Consolidation function')"
        @update:selected-option="onFunctionUpdate"
      />
      <span v-if="model.function === 'quantile'" class="metric-backend-form-consolidation__param">
        <CmkInput
          v-model="quantileInput"
          type="number"
          inline
          :external-errors="showValidationErrors ? quantileErrors : []"
          :aria-label="_t('Quantile (0 to 1)')"
        />
      </span>
      <span
        v-if="model.function === 'fraction_below'"
        class="metric-backend-form-consolidation__param"
      >
        <CmkInput
          v-model="fractionBelowThresholdInput"
          type="number"
          inline
          :external-errors="showValidationErrors ? fractionBelowThresholdErrors : []"
          :aria-label="_t('Threshold')"
        />
      </span>
      <span
        v-if="model.function === 'fraction_between'"
        class="metric-backend-form-consolidation__param"
      >
        <CmkInput
          v-model="fractionLowerThresholdInput"
          type="number"
          inline
          :external-errors="showValidationErrors ? fractionBetweenErrors : []"
          :aria-label="_t('Lower threshold')"
        />
        <span class="metric-backend-form-consolidation__word">–</span>
        <CmkInput
          v-model="fractionUpperThresholdInput"
          type="number"
          inline
          :aria-label="_t('Upper threshold')"
        />
      </span>
      <span class="metric-backend-form-consolidation__lookback">
        <span class="metric-backend-form-consolidation__word">{{ _t('over last') }}</span>
        <CmkTimeSpan
          v-model:data="lookbackInput"
          :label="''"
          :title="_t('Lookback')"
          :input-hint="null"
          :displayed-magnitudes="['minute', 'second']"
          :validators="[]"
          :backend-validation="[]"
        />
      </span>
    </template>
  </InlineEditPill>
</template>

<style scoped>
.metric-backend-form-consolidation__segment {
  padding: var(--dimension-2) var(--dimension-3);
  display: inline-flex;
  align-items: center;
}

.metric-backend-form-consolidation__segment--dimmed {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.metric-backend-form-consolidation__param {
  display: inline-flex;
  align-items: center;
  padding-left: var(--dimension-2);
  position: relative;
}

/* Float the validation message above the pill so it doesn't grow the row and offset the controls. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.metric-backend-form-consolidation__param :deep(.cmk-inline-validation) {
  position: absolute;
  bottom: 100%;
  left: 0;
}

.metric-backend-form-consolidation__lookback {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.metric-backend-form-consolidation__word {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}
</style>
