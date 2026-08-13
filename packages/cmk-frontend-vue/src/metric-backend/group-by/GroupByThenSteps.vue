<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { ref } from 'vue'

import GroupByThenStep from './GroupByThenStep.vue'
import { isKeyValid } from './types'
import type { AggregationStep, GroupKey } from './types'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    groupByKeys: GroupKey[]
    // The host table's label-cell class, so "then" aligns with the host's labels.
    labelClass?: string
  }>(),
  { labelClass: '' }
)

const thenSteps = defineModel<AggregationStep[]>({ required: true })

const pendingOpenId = ref<string | null>(null)

function allowedKeysForStep(index: number): GroupKey[] {
  const source = index === 0 ? props.groupByKeys : (thenSteps.value[index - 1]?.keys ?? [])
  return source.filter(isKeyValid)
}

function addThenStep(): void {
  const step: AggregationStep = { id: randomId(), function: 'avg', keys: [] }
  thenSteps.value = [...thenSteps.value, step]
  pendingOpenId.value = step.id
}

function removeThenStep(targetIndex: number): void {
  thenSteps.value = thenSteps.value.filter((_, index) => index !== targetIndex)
}

function updateThenStep(targetIndex: number, updated: AggregationStep): void {
  thenSteps.value = thenSteps.value.map((step, index) => (index === targetIndex ? updated : step))
}
</script>

<template>
  <tr v-for="(step, index) in thenSteps" :key="step.id">
    <td :class="labelClass">{{ _t('then') }}</td>
    <td>
      <GroupByThenStep
        :model-value="step"
        :allowed-keys="allowedKeysForStep(index)"
        :auto-open="step.id === pendingOpenId"
        @update:model-value="(value) => updateThenStep(index, value)"
        @remove="removeThenStep(index)"
      />
    </td>
  </tr>
  <tr>
    <td :class="labelClass">{{ _t('then') }}</td>
    <td>
      <CmkIconButton
        class="metric-backend-group-by-then-steps__add"
        name="add"
        size="large"
        :title="_t('Add then step')"
        :aria-label="_t('Add then step')"
        @click="addThenStep"
      />
    </td>
  </tr>
</template>

<style scoped>
.metric-backend-group-by-then-steps__add:hover {
  background-color: var(--input-hover-bg-color);
}
</style>
