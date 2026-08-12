<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { computed, ref } from 'vue'

import { MetricsCalculationSlideout, type RefVisibility } from '@/graphing/designer/calculation'
import DeleteWithDependentsPopup from '@/graphing/designer/components/DeleteWithDependentsPopup.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { isComplete } from '@/graphing/designer/drafts'
import {
  DEFAULT_TITLE_MACRO,
  type FormulaDraft,
  type GraphItem,
  type ItemId
} from '@/graphing/designer/types'

import codeExample from './UclMetricsCalculationSlideoutCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const PALETTE: readonly string[] = [
  '#28a2f3',
  '#ff8400',
  '#ec48b6',
  '#ffd703',
  '#8380ff',
  '#1ee6e6',
  '#147d70',
  '#bf8548',
  '#0667c1',
  '#ed3b3b',
  '#15d1a0',
  '#66ffcc'
]

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
  },
  {
    id: 'B',
    type: 'rrd_metric',
    color: PALETTE[1]!,
    title: 'Memory used',
    line_type: 'line',
    mirrored: false,
    visible: true,
    host_name: 'my-host',
    service_name: 'Memory',
    metric_name: 'mem_used',
    consolidation: 'avg'
  },
  {
    id: 'C',
    type: 'rrd_query',
    title: 'HTTP requests (per pod)',
    line_type: 'line',
    mirrored: false,
    visible: true,
    context: { host: { host: 'my-host' } },
    metric_name: 'http_requests',
    consolidation: 'avg'
  },
  {
    id: 'D',
    type: 'rrd_formula',
    color: PALETTE[2]!,
    title: DEFAULT_TITLE_MACRO,
    ast: {
      op: 'difference',
      operands: [
        { op: 'ref', id: 'A' },
        { op: 'ref', id: 'B' }
      ]
    },
    line_type: 'line',
    mirrored: false,
    visible: true
  },
  {
    id: 'E',
    type: 'metric_backend',
    title: 'OTel span latency',
    line_type: 'line',
    mirrored: false,
    visible: true,
    metric_name: 'span.latency',
    attribute_filter: { type: 'and', conjuncts: [] },
    consolidation_function: {
      type: 'histogram_quantile',
      lookback_seconds: 300,
      percentile: 95
    }
  }
]

const store = useGraphItems(PALETTE)
store.replaceAll(seed)
const completeItems = computed(() => store.items.value.filter(isComplete))
const open = ref(false)

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

const pendingDelete = ref<{ id: ItemId; dependents: GraphItem[] } | null>(null)

function onDelete(id: ItemId): void {
  const dependents = store.dependentsOf(id)
  if (dependents.length === 0) {
    store.remove(id)
    return
  }
  pendingDelete.value = { id, dependents }
}

function onConfirmDelete(): void {
  if (pendingDelete.value === null) {
    return
  }
  for (const dependent of pendingDelete.value.dependents) {
    store.remove(dependent.id)
  }
  store.remove(pendingDelete.value.id)
  pendingDelete.value = null
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Metrics calculation slideout</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton variant="primary" @click="open = true">Open "Calculate metrics"</CmkButton>

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
      <DeleteWithDependentsPopup
        v-if="pendingDelete !== null"
        open
        :ids="[pendingDelete.id]"
        :dependents="pendingDelete.dependents"
        @confirm="onConfirmDelete"
        @close="pendingDelete = null"
      />
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>
