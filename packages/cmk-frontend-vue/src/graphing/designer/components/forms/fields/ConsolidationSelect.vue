<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import {
  CONSOLIDATION_FUNCTIONS,
  type ConsolidationFn,
  isConsolidationFn,
  useConsolidationFunctionLabels
} from '@/graphing/components/consolidation'

import SourceFormField from '../SourceFormField.vue'

const { modelValue } = defineProps<{
  modelValue: ConsolidationFn
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ConsolidationFn]
}>()

const { _t } = usei18n()
const labels = useConsolidationFunctionLabels()

const suggestions = computed(() => ({
  type: 'fixed' as const,
  suggestions: CONSOLIDATION_FUNCTIONS.map((name) => ({ name, title: labels.value[name] }))
}))

function onChange(value: string | null): void {
  if (isConsolidationFn(value)) {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <SourceFormField
    v-slot="{ controlId }"
    :label="_t('Then consolidate by')"
    label-variant="description"
    :required="false"
    :errors="[]"
  >
    <CmkDropdown
      :model-value="modelValue"
      :component-id="controlId"
      :options="suggestions"
      :label="_t('Consolidation function')"
      floating
      @update:model-value="onChange"
    />
  </SourceFormField>
</template>
