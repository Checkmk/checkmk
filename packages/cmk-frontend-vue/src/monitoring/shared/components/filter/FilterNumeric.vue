<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="F extends FilterField">
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { CmkRadioButton, CmkRadioGroup } from '@/components/user-input/CmkRadioButton'

import type { ColumnFilterNode, FilterField, NumericOp } from '@/monitoring/shared/api/types'

import CmkNumberRange, { type NumberRange } from './CmkNumberRange.vue'
import type { NumericFilter } from './types'

const props = defineProps<{ definition: NumericFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const emit = defineEmits<{ 'update:valid': [valid: boolean] }>()

const { _t } = usei18n()

const ANY_OPTION = 'any'
const NONE_OPTION = 'none'
const RANGE_OPTION = 'range'

const optionRanges: Record<string, NumberRange> = {
  [ANY_OPTION]: { from: 1, to: undefined },
  [NONE_OPTION]: { from: 0, to: 0 }
}

function extractRange(node: ColumnFilterNode<F> | undefined): NumberRange {
  const range: NumberRange = { from: undefined, to: undefined }
  if (!node) {
    return range
  }
  const conditions = node.type === 'and' ? node.children : [node]
  for (const condition of conditions) {
    if (condition.type !== 'condition' || !('op' in condition)) {
      continue
    }
    if (condition.op === 'gte') {
      range.from = condition.value as number
    } else if (condition.op === 'lte') {
      range.to = condition.value as number
    }
  }
  return range
}

const range = ref<NumberRange>(extractRange(model.value))

function matchesOption(option: string): boolean {
  const preset = optionRanges[option]
  return preset !== undefined && range.value.from === preset.from && range.value.to === preset.to
}

function initialSelection(): string {
  if (matchesOption(ANY_OPTION)) {
    return ANY_OPTION
  }
  if (matchesOption(NONE_OPTION)) {
    return NONE_OPTION
  }
  if (range.value.from !== undefined || range.value.to !== undefined) {
    return RANGE_OPTION
  }
  return ''
}

const selected = ref<string>(initialSelection())

function condition(op: NumericOp, value: number): ColumnFilterNode<F> {
  return {
    type: 'condition',
    field: props.definition.field,
    op,
    value
  } as ColumnFilterNode<F>
}

function createFilterNode(next: NumberRange): void {
  const conditions: ColumnFilterNode<F>[] = []
  if (next.from !== undefined) {
    conditions.push(condition('gte', next.from))
  }
  if (next.to !== undefined) {
    conditions.push(condition('lte', next.to))
  }
  if (conditions.length === 0) {
    model.value = undefined
  } else if (conditions.length === 1) {
    model.value = conditions[0]
  } else {
    model.value = { type: 'and', children: conditions } as ColumnFilterNode<F>
  }
}

watch(selected, (value) => {
  const preset = optionRanges[value]
  range.value = preset ? { ...preset } : { from: undefined, to: undefined }
  createFilterNode(range.value)
})
</script>

<template>
  <div class="monitoring-filter-numeric">
    <CmkRadioGroup v-model="selected" class="monitoring-filter-numeric__radio-group">
      <div class="monitoring-filter-numeric__radio-row">
        <CmkRadioButton :value="ANY_OPTION" :label="_t('Any (>0)')" />
      </div>
      <div class="monitoring-filter-numeric__radio-row">
        <CmkRadioButton :value="NONE_OPTION" :label="_t('None (=0)')" />
      </div>
      <div class="monitoring-filter-numeric__radio-row">
        <CmkRadioButton :value="RANGE_OPTION" :label="_t('Range')" />
      </div>
    </CmkRadioGroup>

    <CmkNumberRange
      v-model="range"
      class="monitoring-filter-numeric__number-range"
      :unit="definition.unit ?? ''"
      :disabled="selected !== RANGE_OPTION"
      @update:model-value="createFilterNode"
      @update:valid="emit('update:valid', $event)"
    />
  </div>
</template>

<style scoped>
.monitoring-filter-numeric {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-filter-numeric__radio-group {
  gap: var(--dimension-2);
}

.monitoring-filter-numeric__radio-row {
  display: flex;
  align-items: center;
  padding: var(--dimension-2);

  &:hover,
  &:focus-within {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-filter-numeric__number-range {
  margin-left: var(--dimension-8);
}
</style>
