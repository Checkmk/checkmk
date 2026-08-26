<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Content component for the "checkbox-list-with-flags" filter type. A thin
composition of FilterCheckboxList (the enum options) and FilterBooleanGroup
(the flags), for columns whose filter mixes an enum with orthogonal boolean
conditions - namely the state column, which also filters on flapping/stale.
Neither child component needs to know about the other; this wrapper only
splits the combined node into each child's own slice and recombines their
edits.

The v-model is a `ColumnFilterNode<F | BF>` (or undefined for "no filter"):
the checkbox list's own `one_of` condition and any active flag's `eq`
condition, AND-combined when more than one is active. The parent
`FilterDropdown` owns the popover shell and Clear/Apply handling.
-->
<script setup lang="ts" generic="F extends FilterField, BF extends FilterField">
import { computed } from 'vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import FilterBooleanGroup from './FilterBooleanGroup.vue'
import FilterCheckboxList from './FilterCheckboxList.vue'
import type { BooleanGroupFilter, CheckboxListFilter, CheckboxListWithFlagsFilter } from './types'

const props = defineProps<{ definition: CheckboxListWithFlagsFilter<F, BF> }>()

const model = defineModel<ColumnFilterNode<F | BF> | undefined>({ default: undefined })

function topLevelConditions(
  node: ColumnFilterNode<F | BF> | undefined
): ColumnFilterNode<F | BF>[] {
  if (!node) {
    return []
  }
  // TS can't fold `FieldConditionMap[F | BF]` (from the narrowed union below)
  // back into `ColumnFilterNode<F | BF>` when F and BF are separate, still
  // abstract type parameters - the cast is for the checker, not a real type
  // mismatch: `node` here is provably a `ColumnFilterNode<F | BF>` already.
  return node.type === 'and' ? node.children : [node as ColumnFilterNode<F | BF>]
}

// Combines the checkbox and flags slices back into one node, flattening a
// slice that is itself an "and" (several active flags) rather than nesting
// it - the model stays a single flat "and" of conditions either way.
function combine(
  nodes: (ColumnFilterNode<F | BF> | undefined)[]
): ColumnFilterNode<F | BF> | undefined {
  const active: ColumnFilterNode<F | BF>[] = nodes
    .filter((node): node is ColumnFilterNode<F | BF> => node !== undefined)
    .flatMap((node) => (node.type === 'and' ? node.children : [node as ColumnFilterNode<F | BF>]))
  if (active.length === 0) {
    return undefined
  }
  return active.length === 1
    ? active[0]
    : ({ type: 'and', children: active } as ColumnFilterNode<F | BF>)
}

function isCheckboxCondition(node: ColumnFilterNode<F | BF>): boolean {
  return node.type === 'condition' && node.field === props.definition.field
}

const checkboxDefinition = computed<CheckboxListFilter<F>>(() => ({
  type: 'checkbox-list',
  field: props.definition.field,
  options: props.definition.options,
  ...(props.definition.searchThreshold !== undefined && {
    searchThreshold: props.definition.searchThreshold
  })
}))

const checkboxModel = computed<ColumnFilterNode<F> | undefined>({
  get: () =>
    topLevelConditions(model.value).find(isCheckboxCondition) as ColumnFilterNode<F> | undefined,
  set: (value) => {
    const flags = topLevelConditions(model.value).filter((node) => !isCheckboxCondition(node))
    model.value = combine([value as ColumnFilterNode<F | BF> | undefined, ...flags])
  }
})

const flagsDefinition = computed<BooleanGroupFilter<BF>>(() => ({
  type: 'boolean-group',
  groups: props.definition.flags
}))

const flagsModel = computed<ColumnFilterNode<BF> | undefined>({
  get: () =>
    combine(topLevelConditions(model.value).filter((node) => !isCheckboxCondition(node))) as
      | ColumnFilterNode<BF>
      | undefined,
  set: (value) => {
    const checkbox = topLevelConditions(model.value).find(isCheckboxCondition)
    model.value = combine([checkbox, value as ColumnFilterNode<F | BF> | undefined])
  }
})
</script>

<template>
  <div class="monitoring-filter-checkbox-list-with-flags">
    <FilterCheckboxList v-model="checkboxModel" :definition="checkboxDefinition" />
    <hr class="monitoring-filter-checkbox-list-with-flags__separator" />
    <FilterBooleanGroup v-model="flagsModel" :definition="flagsDefinition" />
  </div>
</template>

<style scoped>
.monitoring-filter-checkbox-list-with-flags {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.monitoring-filter-checkbox-list-with-flags__separator {
  width: 100%;
  height: var(--dimension-1);
  border: 0;
  background-color: var(--ux-theme-4);
  margin: var(--dimension-1) 0;
}
</style>
