<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import { computed, inject } from 'vue'

import { autonomousSystemSlideInKey, hostSlideInKey } from '@/dashboard/types/injectionKeys.ts'
import type { NetworkFlowTopTableContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import CmkRankedTable from '@/network-flow/CmkRankedTable'
import type { ChartColor, RankedTableColumn, RankedTableRow } from '@/network-flow/CmkRankedTable'

import DashboardContentContainer from '../DashboardContentContainer.vue'
import type { ContentProps } from '../types.ts'
import { useNetworkFlowWidgetData } from './useNetworkFlowWidgetData.ts'

const props = defineProps<ContentProps<NetworkFlowTopTableContent>>()

// null when the dashboard does not wire it up; cells then stay plain text.
const openHostSlideIn = inject(hostSlideInKey, null)
const openAutonomousSystemSlideIn = inject(autonomousSystemSlideInKey, null)

const { data, error } = useNetworkFlowWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowTopTableData(
      props.content,
      props.effective_filter_context.filters
    ),
  (response): { columns: RankedTableColumn[]; rows: RankedTableRow[] } => ({
    columns: response.value.columns,
    rows: response.value.rows
  }),
  () => ({ filters: props.effective_filter_context.filters, content: props.content })
)

// The widget's accent values name colors of the chart palette, so the
// configuration passes straight through (the assignment is type-checked).
const barColor = computed<ChartColor>(() => props.content.accent)

// Make the "host"/"asn" columns clickable to open their slide-ins.
function isClickable(columnKey: string): boolean {
  return (
    (columnKey === 'host' && openHostSlideIn !== null) ||
    (columnKey === 'asn' && openAutonomousSystemSlideIn !== null)
  )
}

const displayColumns = computed<RankedTableColumn[]>(() =>
  (data.value?.columns ?? []).map((column) =>
    isClickable(column.key) ? { ...column, clickable: true } : column
  )
)

function onCellClick(column: RankedTableColumn, row: RankedTableRow): void {
  const value = String(row[column.key] ?? '')
  if (column.key === 'host' && openHostSlideIn) {
    openHostSlideIn(value)
  } else if (column.key === 'asn' && openAutonomousSystemSlideIn) {
    // The cell renders as "AS<n>"; the endpoint wants the numeric ASN.
    const asn = Number(value.replace(/^AS/, ''))
    if (!Number.isNaN(asn)) {
      openAutonomousSystemSlideIn(asn)
    }
  }
}
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-network-flow-top-table__wrapper">
      <div v-if="error" class="db-content-network-flow-top-table__error">
        <CmkAlertBox :variant="error.variant">{{ error.message }}</CmkAlertBox>
      </div>
      <CmkLoading v-else-if="data === undefined" />
      <CmkRankedTable
        v-else
        :columns="displayColumns"
        :rows="data.rows"
        :bar-color="barColor"
        @cell-click="onCellClick"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-network-flow-top-table__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
  padding: var(--spacing);
}

.db-content-network-flow-top-table__error {
  margin: auto;
  max-width: 90%;
}
</style>
