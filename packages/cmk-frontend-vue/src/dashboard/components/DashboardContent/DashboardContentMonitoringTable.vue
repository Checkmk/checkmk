<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { ComputedMonitoringTable, MonitoringTableContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'
import { unreachableSitesHint } from '@/monitoring/shared/unreachableSites'
import MonitoringTableWidget from '@/monitoring/table-widget/MonitoringTableWidget.vue'
import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'
import { monitoringTableRegistry } from '@/monitoring/table-widget/registry'
import type { MonitoringTableDescriptor } from '@/monitoring/table-widget/tableDescriptors'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types'

const props = defineProps<ContentProps<MonitoringTableContent>>()
const { _t } = usei18n()

const { source, headers } = useWidgetSource(props)
const tableState = new WidgetTableState(props.content.sort)
watch([() => props.content.sort.join(','), () => props.content.columns.join(',')], () =>
  tableState.reset(props.content.sort)
)
// The backend computes the rows of the very table the descriptor is looked up for.
const descriptor = computed(
  () =>
    monitoringTableRegistry.descriptor(props.content.table) as MonitoringTableDescriptor<
      ComputedMonitoringTable['rows'][number]
    >
)

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

// The wizard preview has no click shield, so that it scrolls: its links must not navigate away.
function blockLinksInPreview(event: MouseEvent): void {
  if (props.isPreview && event.target instanceof Element && event.target.closest('a')) {
    event.preventDefault()
  }
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
      <div
        class="db-content-monitoring-table"
        @click.capture="blockLinksInPreview"
        @auxclick.capture="blockLinksInPreview"
      >
        <CmkAlert
          v-if="value.unreachable_sites.length > 0"
          class="db-content-monitoring-table__unreachable"
          variant="warning"
          :text="unreachableSitesHint(value.unreachable_sites)"
        />
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
          :display-options="{
            dateFormat: content.date_format,
            timestampFormat: content.timestamp_format
          }"
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

.db-content-monitoring-table__unreachable,
.db-content-monitoring-table__unapplied {
  margin: 0 0 var(--dimension-3);
}

.db-content-monitoring-table__unapplied {
  color: var(--font-color-dimmed);
}

.db-content-monitoring-table__truncated {
  margin: var(--dimension-3) 0 0;
  color: var(--font-color-dimmed);
}
</style>
