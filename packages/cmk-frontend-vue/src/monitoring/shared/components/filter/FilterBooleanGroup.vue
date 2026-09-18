<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Content component for the "boolean-group" filter type. It renders one tri-state
icon-only toggle button group per boolean field: a dash for "Any" (no
condition), a checkmark for "Yes" (has to be true) and an X for "No" (has to be
false). A legend row heads the three columns with the very labels the buttons
carry as their accessible name and tooltip, and each group is named by its own
title, so "Yes" is never read out of context.

Legend and buttons share one grid - the legend row borrows its columns via
subgrid - so a heading sits above the button it heads. The three columns are as
wide as the library makes an icon-only small toggle button, declared once as
`--monitoring-filter-boolean-group-option-width`.

The v-model is a `ColumnFilterNode<F>` (or undefined for "no filter"). Group
states are derived from the model at render time; on change the non-"Any"
groups produce `eq` boolean conditions that are AND-combined into the node (a
single active group stays a lone condition). The parent `FilterDropdown` owns
the popover shell and Clear/Apply handling.
-->
<script setup lang="ts" generic="F extends FilterField">
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import type { BooleanGroupFilter } from './types'

type BooleanState = 'all' | 'true' | 'false'

const props = defineProps<{ definition: BooleanGroupFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const { _t } = usei18n()

function conditionsOf(node: ColumnFilterNode<F> | undefined): { field: F; value: boolean }[] {
  if (!node) {
    return []
  }
  if (node.type === 'condition') {
    return [{ field: node.field as F, value: Boolean(node.value) }]
  }
  if (node.type === 'and') {
    return node.children.flatMap(conditionsOf)
  }
  return []
}

const stateByField = computed<Partial<Record<F, BooleanState>>>(() => {
  const states: Partial<Record<F, BooleanState>> = {}
  for (const condition of conditionsOf(model.value)) {
    states[condition.field] = condition.value ? 'true' : 'false'
  }
  return states
})

function stateOf(field: F): BooleanState {
  return stateByField.value[field] ?? 'all'
}

const options = computed<ToggleButtonOption[]>(() => [
  { label: _t('Any'), value: 'all', icon: 'dash', tooltip: _t('Any') },
  { label: _t('Yes'), value: 'true', icon: 'checkmark', tooltip: _t('Yes') },
  { label: _t('No'), value: 'false', icon: 'cancel', tooltip: _t('No') }
])

function setState(field: F, next: BooleanState): void {
  const active = props.definition.groups
    .map((group) => ({
      field: group.field,
      state: group.field === field ? next : stateOf(group.field)
    }))
    .filter((entry) => entry.state !== 'all')
    .map(
      (entry) =>
        ({
          type: 'condition',
          field: entry.field,
          op: 'eq',
          value: entry.state === 'true'
        }) as ColumnFilterNode<F>
    )

  if (active.length === 0) {
    model.value = undefined
  } else if (active.length === 1) {
    model.value = active[0]
  } else {
    model.value = { type: 'and', children: active } as ColumnFilterNode<F>
  }
}
</script>

<template>
  <div class="monitoring-filter-boolean-group">
    <div class="monitoring-filter-boolean-group__legend" aria-hidden="true">
      <span
        v-for="option in options"
        :key="option.value"
        class="monitoring-filter-boolean-group__legend-label"
        >{{ option.label }}</span
      >
    </div>
    <div
      v-for="group in definition.groups"
      :key="group.field"
      class="monitoring-filter-boolean-group__group"
      role="group"
      :aria-label="group.title"
    >
      <span class="monitoring-filter-boolean-group__title">{{ group.title }}</span>
      <CmkToggleButtonGroup
        class="monitoring-filter-boolean-group__options"
        :options="options"
        :model-value="stateOf(group.field)"
        size="small"
        spacing="none"
        @update:model-value="setState(group.field, $event as BooleanState)"
      />
    </div>
  </div>
</template>

<style scoped>
.monitoring-filter-boolean-group {
  --monitoring-filter-boolean-group-option-width: var(--dimension-8);

  display: grid;
  grid-template-columns: 1fr repeat(3, var(--monitoring-filter-boolean-group-option-width));
  align-items: center;
  row-gap: var(--dimension-4);
  margin: var(--dimension-3) 0;
  padding: var(--dimension-3) var(--dimension-5);
}

.monitoring-filter-boolean-group__legend {
  display: grid;
  grid-column: 2 / -1;
  grid-template-columns: subgrid;
}

.monitoring-filter-boolean-group__legend-label {
  text-align: center;
  font-size: var(--font-size-small);
}

.monitoring-filter-boolean-group__group {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
}

.monitoring-filter-boolean-group__title {
  padding-right: var(--dimension-4);
}

.monitoring-filter-boolean-group__options {
  grid-column: 2 / -1;
}
</style>
