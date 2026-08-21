<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclIconCellCodeExample.vue?raw'

export const panelConfig = {
  downtime: {
    type: 'boolean' as const,
    title: 'downtime',
    initialState: true,
    help: 'Show the scheduled-downtime mode icon, which links to the legacy downtimes view.'
  },
  acknowledged: {
    type: 'boolean' as const,
    title: 'acknowledged',
    initialState: true,
    help: 'Show the acknowledgement mode icon, which links to the legacy host view.'
  },
  eventIcon: {
    type: 'boolean' as const,
    title: 'eventIcon',
    initialState: false,
    help: 'Show an event icon of the History tab, which carries no link and stays read-only.'
  },
  minWidth: {
    type: 'number' as const,
    title: 'minWidth',
    initialState: 80,
    help: 'Minimum column width in px (tanstack column minSize).'
  },
  maxWidth: {
    type: 'number' as const,
    title: 'maxWidth',
    initialState: 120,
    help: 'Maximum column width in px (tanstack column maxSize).'
  },
  justify: {
    type: 'list' as const,
    title: 'justify',
    options: [
      { title: 'left', name: 'left' },
      { title: 'center', name: 'center' },
      { title: 'right', name: 'right' }
    ],
    initialState: 'left',
    help: 'Horizontal alignment of the cell content.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import type { EventIcon, HostMode, MonitoringIcon } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { ColumnJustify } from '@/monitoring/shared/components/MonitoringTableContext'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'

defineProps<{ screenshotMode: boolean }>()

const DOWNTIME_MODE: HostMode = {
  icon_name: 'downtime',
  link: 'view.py?view_name=downtimes_of_host&host=web-server-01',
  title: 'In scheduled downtime'
}

const ACKNOWLEDGED_MODE: HostMode = {
  icon_name: 'ack',
  link: 'view.py?view_name=host&host=web-server-01',
  title: 'Problem acknowledged'
}

const SERVICE_ALERT_EVENT: EventIcon = {
  icon_name: 'alert-crit',
  title: 'Service alert'
}

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const icons = computed<MonitoringIcon[]>(() => {
  const result: MonitoringIcon[] = []
  if (propState.value.downtime) {
    result.push(DOWNTIME_MODE)
  }
  if (propState.value.acknowledged) {
    result.push(ACKNOWLEDGED_MODE)
  }
  if (propState.value.eventIcon) {
    result.push(SERVICE_ALERT_EVENT)
  }
  return result
})

const justify = computed<ColumnJustify>(() => propState.value.justify as ColumnJustify)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Icons',
    enableSorting: false,
    minSize: propState.value.minWidth,
    maxSize: propState.value.maxWidth,
    meta: { justify: justify.value }
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>IconCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-icon-cell__table-wrap">
        <MonitoringTable
          :rows="rows"
          :fetch-state="'idle'"
          :has-loaded="true"
          :columns="columns"
          :sort-state="sortState"
          :filter-state="filterState"
          @update:sort-state="sortState = $event"
          @update:filter-state="filterState = $event"
        >
          <template #row>
            <IconCell column-id="cell" :icons="icons" />
          </template>
        </MonitoringTable>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-icon-cell__table-wrap {
  width: 320px;
}
</style>
