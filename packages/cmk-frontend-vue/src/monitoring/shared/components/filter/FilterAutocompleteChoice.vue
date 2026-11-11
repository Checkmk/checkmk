<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Funnel content for the "autocomplete-choice" filter type: the values of a field
that are known only to the server, picked as chips against its autocompleter.

The committed value is a single set-membership condition carrying every pick,
which is what the API's label, tag and contact-group conditions accept. The
AND/OR switch picks `all_of` or `one_of`; the definition's `op` is the default.
-->
<script setup lang="ts" generic="F extends FilterField">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { ColumnFilterNode, FilterField } from '../../api/types'
import FilterCombineToggle, { type CombineMode } from './FilterCombineToggle.vue'
import type { AutocompleteChoiceFilter } from './types'

type ChoiceOp = 'all_of' | 'one_of'

const OP_BY_MODE: Record<CombineMode, ChoiceOp> = { and: 'all_of', or: 'one_of' }

const props = defineProps<{ definition: AutocompleteChoiceFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

const { _t } = usei18n()

// Remembers a switch flipped before the first pick, which has no condition to carry it yet.
const pickedOp = ref<ChoiceOp | undefined>()

const op = computed<ChoiceOp>(
  () =>
    (model.value?.type === 'condition' ? (model.value.op as ChoiceOp) : undefined) ??
    pickedOp.value ??
    (props.definition.op as ChoiceOp)
)

const mode = computed<CombineMode>({
  get: () => (op.value === 'all_of' ? 'and' : 'or'),
  set: (next) => {
    pickedOp.value = OP_BY_MODE[next]
    if (model.value?.type === 'condition') {
      model.value = { ...model.value, op: OP_BY_MODE[next] } as ColumnFilterNode<F>
    }
  }
})

const selected = computed<string[]>({
  get() {
    const node = model.value
    if (!node || node.type !== 'condition' || !Array.isArray(node.value)) {
      return []
    }
    return node.value as string[]
  },
  set(values: string[]) {
    if (values.length === 0) {
      model.value = undefined
      return
    }
    model.value = {
      type: 'condition',
      field: props.definition.field,
      op: op.value,
      value: values
    } as ColumnFilterNode<F>
  }
})
</script>

<template>
  <div class="monitoring-filter-autocomplete-choice">
    <CmkChipAutocomplete
      v-model="selected"
      :suggest="definition.suggest"
      :suggest-when-empty="definition.suggestWhenEmpty"
      :key-value="definition.keyValue"
      :wildcard-option="definition.wildcardOption"
      :max-selected="definition.maxSelected"
    />
    <FilterCombineToggle v-model="mode" :label="_t('Combine selections with')" />
  </div>
</template>

<style scoped>
.monitoring-filter-autocomplete-choice {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin: var(--dimension-3) var(--dimension-2);
}
</style>
