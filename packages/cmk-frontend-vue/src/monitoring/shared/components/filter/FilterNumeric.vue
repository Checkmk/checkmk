<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="F extends FilterField">
import { ref } from 'vue'

import type { ColumnFilterNode, FilterField, NumericOp } from '@/monitoring/shared/api/types'

import CmkNumberRange, { type NumberRange } from './CmkNumberRange.vue'
import type { NumericFilter, NumericPreset } from './types'

const props = defineProps<{ definition: NumericFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const emit = defineEmits<{ 'update:valid': [valid: boolean] }>()

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

function isPresetActive(preset: NumericPreset): boolean {
  return range.value.from === preset.from && range.value.to === preset.to
}

function applyPreset(preset: NumericPreset): void {
  range.value = isPresetActive(preset)
    ? { from: undefined, to: undefined }
    : { from: preset.from, to: preset.to }
  createFilterNode(range.value)
}
</script>

<template>
  <div class="monitoring-filter-numeric">
    <div
      v-if="definition.presets && definition.presets.length > 0"
      class="monitoring-filter-numeric__presets"
    >
      <button
        v-for="preset in definition.presets"
        :key="preset.label"
        type="button"
        class="monitoring-filter-numeric__chip"
        :class="{ 'monitoring-filter-numeric__chip--active': isPresetActive(preset) }"
        :aria-pressed="isPresetActive(preset)"
        @click="applyPreset(preset)"
      >
        {{ preset.label }}
      </button>
    </div>

    <CmkNumberRange
      v-model="range"
      :unit="definition.unit ?? ''"
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

.monitoring-filter-numeric__presets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-2);
}

.monitoring-filter-numeric__chip {
  padding: var(--dimension-2) var(--dimension-4);
  font: inherit;
  color: var(--font-color);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: 9999px;
  cursor: pointer;

  &:hover {
    background: var(--ux-theme-3);
  }

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 1px;
  }
}

.monitoring-filter-numeric__chip--active {
  color: var(--success);
  border-color: var(--success);
}
</style>
