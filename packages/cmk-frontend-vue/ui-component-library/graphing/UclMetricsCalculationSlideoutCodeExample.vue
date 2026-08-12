<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import { MetricsCalculationSlideout, type RefVisibility } from '@/graphing/designer/calculation'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import type { FormulaDraft, GraphItem, ItemId } from '@/graphing/designer/types'
import { isValid } from '@/graphing/designer/validation'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400', '#ec48b6', '#ffd703']

const seed: GraphItem[] = [
  {
    id: 'A',
    type: 'rrd_metric',
    color: PALETTE[0]!,
    title: 'CPU utilization',
    line_type: 'line',
    mirrored: false,
    visible: true,
    host_name: 'my-host',
    service_name: 'CPU utilization',
    metric_name: 'util',
    consolidation: 'avg'
  }
]

const store = useGraphItems(PALETTE)
store.replaceAll(seed)
const completeItems = computed(() => store.items.value.filter(isValid))
const open = ref(true)

function applyRefVisibility(refVisibility: RefVisibility): void {
  if (refVisibility !== null) {
    store.setVisibility(refVisibility.ids, refVisibility.visible)
  }
}

function onAdd(draft: FormulaDraft, refVisibility: RefVisibility): void {
  store.addFormula(draft)
  applyRefVisibility(refVisibility)
}

function onUpdate(id: ItemId, draft: FormulaDraft, refVisibility: RefVisibility): void {
  store.updateFormula(id, draft)
  applyRefVisibility(refVisibility)
}

function onDelete(id: ItemId): void {
  for (const dependent of store.dependentsOf(id)) {
    store.remove(dependent.id)
  }
  store.remove(id)
}
</script>

<template>
  <MetricsCalculationSlideout
    :open="open"
    :items="completeItems"
    :next-id="store.nextId.value"
    :next-color="store.nextColor.value"
    @add="onAdd"
    @update="onUpdate"
    @delete="onDelete"
    @close="open = false"
  />
</template>
