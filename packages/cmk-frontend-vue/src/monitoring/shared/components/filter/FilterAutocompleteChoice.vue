<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Funnel content for the "autocomplete-choice" filter type: the values of a field
that are known only to the server, picked as chips against its autocompleter.

The committed value is a single `one_of` condition carrying every pick, which is
what the API's label, tag and contact-group conditions accept.
-->
<script setup lang="ts" generic="F extends FilterField">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import { computed } from 'vue'

import type { ColumnFilterNode, FilterField } from '../../api/types'
import type { AutocompleteChoiceFilter } from './types'

const props = defineProps<{ definition: AutocompleteChoiceFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })

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
      op: 'one_of',
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
  </div>
</template>

<style scoped>
.monitoring-filter-autocomplete-choice {
  margin: var(--dimension-3) var(--dimension-2);
}
</style>
