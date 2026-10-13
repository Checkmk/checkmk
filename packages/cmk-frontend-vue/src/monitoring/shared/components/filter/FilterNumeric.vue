<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="F extends FilterField">
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

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
  return RANGE_OPTION
}

const selected = ref<string>(initialSelection())

const options = computed<ToggleButtonOption[]>(() => [
  { label: _t('Range'), value: RANGE_OPTION },
  { label: _t('At least one'), value: ANY_OPTION },
  { label: _t('None'), value: NONE_OPTION }
])

const presetInfo = computed<string>(() => {
  if (selected.value === ANY_OPTION) {
    return props.definition.anyInfo ?? _t('Shows rows with a value above 0.')
  }
  if (selected.value === NONE_OPTION) {
    return props.definition.noneInfo ?? _t('Shows rows with a value of 0.')
  }
  return ''
})

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
  if (value !== RANGE_OPTION) {
    emit('update:valid', true)
  }
})
</script>

<template>
  <div class="monitoring-filter-numeric">
    <div class="monitoring-filter-numeric__options" role="group" :aria-label="_t('Value range')">
      <CmkToggleButtonGroup v-model="selected" :options="options" size="small" spacing="none" />
    </div>

    <CmkNumberRange
      v-if="selected === RANGE_OPTION"
      v-model="range"
      class="monitoring-filter-numeric__number-range"
      :unit="definition.unit ?? ''"
      @update:model-value="createFilterNode"
      @update:valid="emit('update:valid', $event)"
    />
    <p v-else-if="presetInfo" class="monitoring-filter-numeric__info">{{ presetInfo }}</p>
  </div>
</template>

<style scoped>
.monitoring-filter-numeric {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding: var(--dimension-3) var(--dimension-5) var(--dimension-4) var(--dimension-5);
}

.monitoring-filter-numeric__options {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding: 0 var(--dimension-2);
}

.monitoring-filter-numeric__number-range {
  padding: 0 var(--dimension-2);
}

.monitoring-filter-numeric__info {
  margin: 0;
  padding: 0 var(--dimension-2);
}
</style>
