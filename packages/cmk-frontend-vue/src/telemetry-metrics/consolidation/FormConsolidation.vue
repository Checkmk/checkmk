<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import type { Section, Suggestions } from 'cmk-ui-library/components/CmkSuggestions/types'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkTimeSpan from 'cmk-ui-library/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'
import {
  type Magnitude,
  minimumSecondsValidator
} from 'cmk-ui-library/components/user-input/CmkTimeSpan/timeSpan'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import InlineEditPill from '../InlineEditPill.vue'
import { useHistogramParams } from '../histogram-params'
import {
  compactFunction,
  functionOptionLabel,
  lookbackLabel,
  typeLabel
} from './consolidation-label'
import { CONSOLIDATION_CATALOG, DEFAULT_QUANTILE, METRIC_TYPES } from './types'
import type {
  ConsolidationFunction,
  ConsolidationFunctionName,
  ConsolidationModel,
  ConsolidationParams,
  MetricType
} from './types'

const { _t } = usei18n()

const props = defineProps<{
  // The metric types the backend resolved for the current metric.
  // An empty list results in every type's functions to be offered.
  availableTypes: MetricType[]
  label?: TranslatedString | undefined
}>()

const model = defineModel<ConsolidationModel>({ required: true })

const typeToken = computed(() => `[${model.value.type}]`)
const functionToken = computed(() => compactFunction(model.value))
const lookbackToken = computed(() => lookbackLabel(model.value.lookbackSeconds))

// Keep the current pick reachable even when the backend did not resolve its type.
const candidateTypes = computed<MetricType[]>(() => {
  if (props.availableTypes.length === 0) {
    return [...METRIC_TYPES]
  }
  return props.availableTypes.includes(model.value.type)
    ? props.availableTypes
    : [model.value.type, ...props.availableTypes]
})

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

function applyFunction(fn: ConsolidationFunction): void {
  // Reset params; they belonged to the previous function. Seed the quantile
  // default so its field isn't blank the moment the function is picked.
  const params: ConsolidationParams =
    fn.function === 'histogram_quantile' ? { quantile: DEFAULT_QUANTILE } : {}
  model.value = { ...model.value, ...fn, params }
}

function onFunctionUpdate(value: string | null): void {
  if (value === null) {
    return
  }
  const [type, fn] = value.split(':') as [MetricType, ConsolidationFunctionName]
  applyFunction({ type, function: fn } as ConsolidationFunction)
}

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

// Both consumers must share these so the validation message matches the shown fields.
const lookbackMagnitudes: Magnitude[] = ['minute', 'second']
// The backend rejects a sub-second lookback.
const lookbackValidators = [minimumSecondsValidator(1, lookbackMagnitudes, _t)]

function setParam(key: keyof ConsolidationParams, value: number | undefined): void {
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
  switch (model.value.function) {
    case 'histogram_quantile':
      return quantileErrors.value
    case 'histogram_fraction_below':
      return fractionBelowThresholdErrors.value
    case 'histogram_fraction_between':
      return fractionBetweenErrors.value
    default:
      return []
  }
})

const lookbackErrors = ref<string[]>([])

const validationMessages = computed<string[]>(() =>
  showValidationErrors.value ? [...activeErrors.value, ...lookbackErrors.value] : []
)

// Veto leaving while a param or the lookback is invalid, revealing the error on the first attempt.
function canLeaveEdit(): boolean {
  if (activeErrors.value.length > 0 || lookbackErrors.value.length > 0) {
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
  <div class="metric-backend-form-consolidation">
    <CmkInlineValidation :validation="validationMessages" />
    <InlineEditPill
      :editing="editing"
      :can-leave="canLeaveEdit"
      :aria-label="label"
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
          floating
          :model-value="dropdownValue"
          :options="functionOptions"
          :label="_t('Consolidation function')"
          @update:model-value="onFunctionUpdate"
        />
        <span
          v-if="model.function === 'histogram_quantile'"
          class="metric-backend-form-consolidation__param"
        >
          <CmkInput
            v-model="quantileInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? quantileErrors : []"
            hide-validation-message
            :aria-label="_t('Quantile (0 to 1)')"
          />
        </span>
        <span
          v-if="model.function === 'histogram_fraction_below'"
          class="metric-backend-form-consolidation__param"
        >
          <CmkInput
            v-model="fractionBelowThresholdInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? fractionBelowThresholdErrors : []"
            hide-validation-message
            :aria-label="_t('Threshold')"
          />
        </span>
        <span
          v-if="model.function === 'histogram_fraction_between'"
          class="metric-backend-form-consolidation__param"
        >
          <CmkInput
            v-model="fractionLowerThresholdInput"
            type="number"
            inline
            :external-errors="showValidationErrors ? fractionBetweenErrors : []"
            hide-validation-message
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
            v-model="lookbackInput"
            :aria-label="_t('Lookback')"
            :label="''"
            :title="''"
            :input-hint="null"
            :displayed-magnitudes="lookbackMagnitudes"
            :validators="lookbackValidators"
            :show-field-errors="showValidationErrors"
            hide-validation-message
            @update:validation="lookbackErrors = $event"
          />
        </span>
      </template>
    </InlineEditPill>
  </div>
</template>

<style scoped>
.metric-backend-form-consolidation {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-2);
}

.metric-backend-form-consolidation__segment {
  padding: var(--dimension-2) 0;
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
  gap: var(--dimension-2);
}

.metric-backend-form-consolidation__lookback {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.metric-backend-form-consolidation__word {
  display: inline-flex;
  align-items: center;
  color: var(--font-color-dimmed);
  white-space: nowrap;
}
</style>
