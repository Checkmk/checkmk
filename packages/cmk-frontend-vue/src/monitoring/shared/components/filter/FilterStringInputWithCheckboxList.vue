<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="F extends FilterField, CF extends FilterField">
import { computed } from 'vue'

import type { ColumnFilterNode, FilterField, FilterNode } from '@/monitoring/shared/api/types'
import { getTopLevelConditions, setCondition } from '@/monitoring/shared/services/filterNodeUtils'

import FilterCheckboxList from './FilterCheckboxList.vue'
import FilterStringInput from './FilterStringInput.vue'
import type {
  CheckboxListFilter,
  StringInputFilter,
  StringInputWithCheckboxListFilter
} from './types'

const props = defineProps<{ definition: StringInputWithCheckboxListFilter<F, CF> }>()

const model = defineModel<ColumnFilterNode<F | CF> | undefined>({ default: undefined })

function withCheckbox(
  node: ColumnFilterNode<F | CF> | undefined,
  checkbox: ColumnFilterNode<CF> | undefined
): ColumnFilterNode<F | CF> | undefined {
  return setCondition(
    node as FilterNode | undefined,
    props.definition.checkboxField,
    checkbox as FilterNode | undefined
  ) as ColumnFilterNode<F | CF> | undefined
}

const stringInputDefinition = computed<StringInputFilter<F>>(() => ({
  type: 'string-input',
  field: props.definition.field
}))

const stringInputModel = computed<ColumnFilterNode<F> | undefined>({
  get: () => withCheckbox(model.value, undefined) as ColumnFilterNode<F> | undefined,
  set: (value) => {
    model.value = withCheckbox(value as ColumnFilterNode<F | CF> | undefined, checkboxModel.value)
  }
})

const checkboxDefinition = computed<CheckboxListFilter<CF>>(() => ({
  type: 'checkbox-list',
  field: props.definition.checkboxField,
  options: props.definition.options,
  ...(props.definition.searchThreshold !== undefined && {
    searchThreshold: props.definition.searchThreshold
  })
}))

const checkboxModel = computed<ColumnFilterNode<CF> | undefined>({
  get: () =>
    (model.value !== undefined
      ? getTopLevelConditions(model.value as FilterNode).find(
          (node) => node.field === props.definition.checkboxField
        )
      : undefined) as ColumnFilterNode<CF> | undefined,
  set: (value) => {
    model.value = withCheckbox(model.value, value)
  }
})
</script>

<template>
  <div class="monitoring-filter-string-input-with-checkbox-list">
    <FilterStringInput v-model="stringInputModel" :definition="stringInputDefinition" />
    <FilterCheckboxList v-model="checkboxModel" :definition="checkboxDefinition" />
  </div>
</template>

<style scoped>
.monitoring-filter-string-input-with-checkbox-list {
  display: flex;
  flex-direction: column;
}
</style>
