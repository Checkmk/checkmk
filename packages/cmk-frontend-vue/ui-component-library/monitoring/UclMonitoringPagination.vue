<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclMonitoringPagination.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'The control is a <nav> labelled "Pages" holding the range label and the two page buttons, which sit in the natural tab order. A button disabled at the first or last page is skipped.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Move to the previous or next page. Each button carries an aria-label ("Previous page" / "Next page") rather than relying on its icon.'
  },
  {
    keys: [],
    description:
      'The range label is aria-live="polite", so paging announces the new range without moving focus.'
  }
]

export const panelConfig = {
  matched: {
    type: 'number' as const,
    title: 'Matched rows',
    initialState: 1247302,
    help: 'How many rows the current query matches. Positions are grouped with Intl.NumberFormat, never the SI formatter - row 1000 must not read as "1 k".'
  },
  limit: {
    type: 'number' as const,
    title: 'Rows per page',
    initialState: 500,
    help: 'The requested batch size. Changing it resets the offset to zero, the same way a new search, sort or filter does.'
  },
  maxOffset: {
    type: 'number' as const,
    title: 'Max offset',
    initialState: 50000,
    help: 'The backend cap on how deep paging may go. Next stops there even when more rows match - lower it below the matched count to see the last reachable page.'
  },
  unit: {
    type: 'string' as const,
    title: 'Unit',
    initialState: 'flows',
    help: 'Appended to the range label. Leave empty for a bare "1-500 of 1 247 302".'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, provide, ref, watch } from 'vue'

import MonitoringPagination from '@/monitoring/shared/components/MonitoringPagination.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const offset = ref(0)

const matched = computed(() => Math.max(0, propState.value.matched))
const limit = computed(() => Math.max(1, propState.value.limit))
const maxOffset = computed(() => Math.max(0, propState.value.maxOffset))

// Mirrors MonitoringService: any change that can renarrow or resize the result
// set puts the reader back on the first page.
watch([matched, limit, maxOffset], () => {
  offset.value = 0
})

const pageFirst = computed(() => (matched.value === 0 ? 0 : offset.value + 1))
const pageLast = computed(() => Math.min(offset.value + limit.value, matched.value))
const hasPreviousPage = computed(() => offset.value > 0)
const hasNextPage = computed(
  () => pageLast.value < matched.value && offset.value + limit.value <= maxOffset.value
)

// The real service is a class with fetching, polling and column state; the
// pagination control only ever touches these members, so the demo stands in
// with exactly them.
const demoService = {
  pageFirst,
  pageLast,
  matched,
  hasPreviousPage,
  hasNextPage,
  nextPage() {
    offset.value += limit.value
  },
  previousPage() {
    offset.value = Math.max(0, offset.value - limit.value)
  }
}

provide(MONITORING_SERVICE, demoService as unknown as MonitoringService<unknown>)

// An empty unit means "no unit", which the component spells as an absent prop
// rather than an explicit undefined.
const unitProps = computed(() => (propState.value.unit ? { unit: propState.value.unit } : {}))

const page = computed(() => Math.floor(offset.value / limit.value) + 1)
const pages = computed(() => Math.max(1, Math.ceil(matched.value / limit.value)))
const reachablePages = computed(() =>
  Math.max(
    1,
    Math.floor(Math.min(maxOffset.value, Math.max(0, matched.value - 1)) / limit.value) + 1
  )
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Monitoring pagination</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-monitoring-pagination__stack">
        <div class="ucl-monitoring-pagination__toolbar">
          <MonitoringPagination v-bind="unitProps" />
        </div>

        <p class="ucl-monitoring-pagination__readout">
          Offset <code>{{ offset }}</code> · page <code>{{ page }}</code> of
          <code>{{ pages }}</code>
          <span v-if="reachablePages < pages">
            (only <code>{{ reachablePages }}</code> reachable within the max offset)</span
          >
        </p>

        <p class="ucl-monitoring-pagination__hint">
          Offset paging for listings whose backend can seek, such as the flow explorer's SQL
          queries. The control renders nothing at all while a single page covers the result set, so
          the total count beside it is left to state the size on its own. It reads its state from
          the injected MonitoringService (<code>pageFirst</code> / <code>pageLast</code> /
          <code>matched</code>) and pages through <code>nextPage()</code> /
          <code>previousPage()</code>, so a view opts in purely by rendering it. Note that
          Livestatus-backed listings cannot seek by offset and page by cursor instead, so they do
          not use this control.
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-monitoring-pagination__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-monitoring-pagination__toolbar {
  display: flex;
  justify-content: flex-end;
  padding: var(--dimension-4);
  background: var(--ux-theme-2);
  border-radius: 4px;
}

.ucl-monitoring-pagination__readout,
.ucl-monitoring-pagination__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
