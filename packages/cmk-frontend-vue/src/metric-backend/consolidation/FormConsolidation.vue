<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'

import InlineEditPill from '../InlineEditPill.vue'
import { compactFunction, lookbackLabel } from './consolidation-label'
import type { ConsolidationModel } from './types'

const { _t } = usei18n()

const model = defineModel<ConsolidationModel>({ required: true })

const typeToken = computed(() => `[${model.value.type}]`)
const functionToken = computed(() => compactFunction(model.value))
const lookbackToken = computed(() => lookbackLabel(model.value.lookbackSeconds))

const editing = ref(false)

const lookbackRef = useTemplateRef<HTMLElement>('lookbackRef')

function onEdit(): void {
  editing.value = true
  void nextTick(() => lookbackRef.value?.querySelector<HTMLInputElement>('input')?.focus())
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
      <span class="metric-backend-form-consolidation__segment">{{ functionToken }}</span>
      <span ref="lookbackRef" class="metric-backend-form-consolidation__lookback">
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
