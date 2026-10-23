<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { ComputedMonitoringTable, MonitoringTableContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'
import MonitoringTableWidget from '@/monitoring/table-widget/MonitoringTableWidget.vue'
import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'
import { monitoringTableRegistry } from '@/monitoring/table-widget/registry'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types'

const props = defineProps<ContentProps<MonitoringTableContent>>()
const { _t } = usei18n()

const { source, headers } = useWidgetSource(props)
const tableState = new WidgetTableState(props.content.sort)
watch([() => props.content.sort.join(','), () => props.content.columns.join(',')], () =>
  tableState.reset(props.content.sort)
)
const descriptor = computed(() => monitoringTableRegistry.descriptor(props.content.table))

const { state, retry } = useWidgetData<ComputedMonitoringTable>(
  () =>
    dashboardAPI.computeMonitoringTable(
      { source: source.value, sort: tableState.encodedSort() },
      headers
    ),
  () => [props.content, props.effective_filter_context, tableState.sortState.value],
  () => props.tick
)

function unappliedHint(value: ComputedMonitoringTable): string {
  return _t('Not applied to this table: %{filters}', {
    filters: value.unapplied_filters.map((filter) => filter.title).join(', ')
  })
}

function truncatedHint(value: ComputedMonitoringTable): string {
  return descriptor.value.truncatedHint(value.rows.length, value.matched)
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
      <div class="db-content-monitoring-table">
        <p
          v-if="value.unapplied_filters.length > 0"
          class="db-content-monitoring-table__unapplied"
          role="note"
        >
          {{ unappliedHint(value) }}
        </p>
        <MonitoringTableWidget
          :descriptor="descriptor"
          :column-ids="content.columns"
          :rows="value.rows"
          :table-state="tableState"
        />
        <p v-if="value.matched > value.rows.length" class="db-content-monitoring-table__truncated">
          {{ truncatedHint(value) }}
        </p>
      </div>
    </template>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-monitoring-table {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.db-content-monitoring-table__unapplied {
  margin: 0 0 var(--dimension-3);
  color: var(--font-color-dimmed);
}

.db-content-monitoring-table__truncated {
  margin: var(--dimension-3) 0 0;
  color: var(--font-color-dimmed);
}
</style>
