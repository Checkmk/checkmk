<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import type { Section, Suggestions } from '@/components/CmkSuggestions/types'
import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'

import InlineEditPill from '../InlineEditPill.vue'
import {
  compactFunction,
  functionOptionLabel,
  lookbackLabel,
  typeLabel
} from './consolidation-label'
import { CONSOLIDATION_CATALOG } from './types'
import type { ConsolidationFunction, ConsolidationModel, MetricType } from './types'

const { _t } = usei18n()

const props = defineProps<{
  // Metric types the backend resolved for the current metric.
  availableTypes: MetricType[]
}>()

const model = defineModel<ConsolidationModel>({ required: true })

const typeToken = computed(() => `[${model.value.type}]`)
const functionToken = computed(() => compactFunction(model.value))
const lookbackToken = computed(() => lookbackLabel(model.value.lookbackSeconds))

function suggestionsForType(type: MetricType) {
  return CONSOLIDATION_CATALOG[type].map((spec) => ({
    name: `${type}:${spec.fn}`,
    title: functionOptionLabel(type, spec.fn, spec.raw)
  }))
}

const functionOptions = computed<Suggestions>(() => {
  // More than one type is ambiguous: group per type so the choice also fixes it.
  if (props.availableTypes.length > 1) {
    const sections: Section[] = props.availableTypes.map((type) => ({
      title: _t('Treat as %{type}', { type: typeLabel(type) }),
      suggestions: suggestionsForType(type)
    }))
    return { type: 'fixed', suggestions: sections }
  }
  return { type: 'fixed', suggestions: suggestionsForType(props.availableTypes[0]!) }
})

const dropdownValue = computed(() => `${model.value.type}:${model.value.function}`)

function onFunctionUpdate(value: string | null): void {
  if (value === null) {
    return
  }
  const [type, fn] = value.split(':') as [MetricType, ConsolidationFunction]
  // Reset params; they belonged to the previous function.
  model.value = { ...model.value, type, function: fn, params: {} }
}

const editing = ref(false)

const functionDropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('functionDropdownRef')

function onEdit(): void {
  editing.value = true
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

const editAriaLabel = computed(
  () =>
    `${_t('Edit consolidation')}: ${typeToken.value} ${functionToken.value} ${lookbackToken.value}`
)
</script>

<template>
  <InlineEditPill
    :editing="editing"
    :tab-focusable="false"
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
        :model-value="dropdownValue"
        :options="functionOptions"
        :label="_t('Consolidation function')"
        @update:model-value="onFunctionUpdate"
      />
      <span class="metric-backend-form-consolidation__lookback">
        <span class="metric-backend-form-consolidation__word">{{ _t('over last') }}</span>
        <CmkTimeSpan
          v-model="lookbackInput"
          :aria-label="_t('Lookback')"
          :label="''"
          :title="''"
          :input-hint="null"
          :displayed-magnitudes="['minute', 'second']"
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
