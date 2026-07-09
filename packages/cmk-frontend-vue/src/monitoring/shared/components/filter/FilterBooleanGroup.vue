<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Content component for the "boolean-group" filter type. It renders one tri-state
radio group per boolean field, separated by a divider: "All" (no condition), the
field's own label (has to be true) and "NOT <label>" (has to be false).

The v-model is a `ColumnFilterNode<F>` (or undefined for "no filter"). Group
states are derived from the model at render time; on change the non-"all"
groups produce `eq` boolean conditions that are AND-combined into the node (a
single active group stays a lone condition). The parent `FilterDropdown` owns
the popover shell and Clear/Apply handling.
-->
<script setup lang="ts" generic="F extends FilterField">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import { CmkRadioButton, CmkRadioGroup } from '@/components/user-input/CmkRadioButton'

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
    <template v-for="(group, index) in definition.groups" :key="group.field">
      <hr v-if="index > 0" class="monitoring-filter-boolean-group__separator" />
      <CmkRadioGroup
        class="monitoring-filter-boolean-group__group"
        :model-value="stateOf(group.field)"
        @update:model-value="setState(group.field, $event as BooleanState)"
      >
        <CmkRadioButton value="all" :label="_t('All')" />
        <CmkRadioButton value="true" :label="untranslated(group.title)" />
        <CmkRadioButton value="false" :label="untranslated(`NOT ${group.title}`)" />
      </CmkRadioGroup>
    </template>
  </div>
</template>

<style scoped>
.monitoring-filter-boolean-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.monitoring-filter-boolean-group__group {
  padding: 0 var(--dimension-2);
}

.monitoring-filter-boolean-group__separator {
  width: 100%;
  height: var(--dimension-1);
  border: 0;
  background-color: var(--ux-theme-4);
  margin: 0;
}
</style>
