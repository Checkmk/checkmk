<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { explicitWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { NetworkFlowTopTableContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import { chartColorCss } from '@/network-flow/colors'
import { autonomousSystemSlideInKey, hostSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

import WidgetFigureFrame from '../figures/WidgetFigureFrame.vue'
import type { ContentProps } from '../types.ts'

const props = defineProps<ContentProps<NetworkFlowTopTableContent>>()

// null when the dashboard does not wire it up; cells then stay plain text.
const openHostSlideIn = inject(hostSlideInKey, null)
const openAutonomousSystemSlideIn = inject(autonomousSystemSlideInKey, null)

const { state, retry } = useWidgetData(
  () => dashboardAPI.computeNetworkFlowTopTable({ source: explicitWidgetSource(props) }),
  () => [props.content, props.effective_filter_context],
  () => props.tick
)

// The widget's accent values name colors of the chart palette, so the
// configuration passes straight through (the assignment is type-checked).
const barColor = computed<string>(() => chartColorCss(props.content.accent))

// Make the "host"/"asn" columns clickable to open their slide-ins.
function isClickable(columnKey: string): boolean {
  return (
    (columnKey === 'host' && openHostSlideIn !== null) ||
    (columnKey === 'asn' && openAutonomousSystemSlideIn !== null)
  )
}

function displayColumns(columns: RankedTableColumn[]): RankedTableColumn[] {
  return columns.map((column) =>
    isClickable(column.key) ? { ...column, clickable: true } : column
  )
}

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
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value }">
      <div class="db-content-network-flow-top-table__wrapper">
        <CmkRankedTable
          :columns="displayColumns(value.columns)"
          :rows="value.rows"
          :bar-color="barColor"
          @cell-click="onCellClick"
        />
      </div>
    </template>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-network-flow-top-table__wrapper {
  display: flex;
  box-sizing: border-box;
  height: 100%;
  padding: var(--spacing);
}
</style>
