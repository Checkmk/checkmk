<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { ConsolidationFn } from '@/graphing/components/consolidation'

import { resolveMetricColor } from '../../api'
import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftRRDMetricItem } from '../../drafts'
import ConsolidationSelect from './fields/ConsolidationSelect.vue'
import HostNameSelect from './fields/HostNameSelect.vue'
import ServiceMetricSelect from './fields/ServiceMetricSelect.vue'
import ServiceNameSelect from './fields/ServiceNameSelect.vue'
import { hostServiceContext } from './fields/utils'

const { item, store, hostNameErrors, serviceNameErrors, metricNameErrors } = defineProps<{
  item: DraftRRDMetricItem
  store: GraphItemsStore
  hostNameErrors: TranslatedString[]
  serviceNameErrors: TranslatedString[]
  metricNameErrors: TranslatedString[]
}>()

const metricContext = computed(() => hostServiceContext(item.host_name, item.service_name))

/** Selecting upstream clears the dependent selections (host -> service -> metric). */
function onHostChange(hostName: string | null): void {
  store.replace({ ...item, host_name: hostName, service_name: null, metric_name: null })
}

function onServiceChange(serviceName: string | null): void {
  store.replace({ ...item, service_name: serviceName, metric_name: null })
}

async function onMetricChange(metricName: string | null): Promise<void> {
  store.replace({ ...item, metric_name: metricName })
  if (metricName === null) {
    return
  }
  let color: string | null
  try {
    color = await resolveMetricColor(metricName)
  } catch {
    // The canonical color is cosmetic — keep the row's current color.
    return
  }
  // Skip stale responses: the row may be gone or on another metric by now.
  const rowStillExists = store.items.value.some((candidate) => candidate.id === item.id)
  if (color !== null && rowStillExists && item.metric_name === metricName) {
    store.patch(item.id, { color })
  }
}

function onConsolidationChange(value: ConsolidationFn): void {
  store.replace({ ...item, consolidation: value })
}
</script>

<template>
  <div class="graphing-rrd-metric-form">
    <HostNameSelect
      :model-value="item.host_name"
      required
      :errors="hostNameErrors"
      @update:model-value="onHostChange"
    />
    <ServiceNameSelect
      :model-value="item.service_name"
      :host-name="item.host_name"
      required
      :errors="serviceNameErrors"
      @update:model-value="onServiceChange"
    />
    <ServiceMetricSelect
      :model-value="item.metric_name"
      :context="metricContext"
      required
      :errors="metricNameErrors"
      @update:model-value="onMetricChange"
    />
    <ConsolidationSelect
      :model-value="item.consolidation"
      @update:model-value="onConsolidationChange"
    />
  </div>
</template>

<style scoped>
.graphing-rrd-metric-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
}
</style>
