<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts" generic="F extends FilterField">
import { ref } from 'vue'

import CmkInput from '@/components/user-input/CmkInput.vue'

import type { ColumnFilterNode, FilterField } from '../../api/types'
import type { StringInputFilter } from './types'

const props = defineProps<{ definition: StringInputFilter<F> }>()

const model = defineModel<ColumnFilterNode<F> | undefined>({ default: undefined })
function extractValues(node: ColumnFilterNode<F> | undefined): string {
  if (!node || node.type !== 'condition') {
    return ''
  }
  return typeof node.value === 'string' ? node.value : ''
}
const value = ref<string>(extractValues(model.value))

function createFilterNode(raw: string | undefined): void {
  const trimmed = (raw ?? '').trim()
  if (trimmed === '') {
    model.value = undefined
  } else {
    model.value = {
      type: 'condition',
      field: props.definition.field,
      op: 'contains',
      value: trimmed
    } as ColumnFilterNode<F>
  }
}
</script>

<template>
  <CmkInput
    v-model="value"
    class="monitoring-filter-string-input"
    field-size="medium"
    @update:model-value="createFilterNode($event)"
  />
</template>
