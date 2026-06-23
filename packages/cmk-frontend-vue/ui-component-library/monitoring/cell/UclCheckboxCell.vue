<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCheckboxCellCodeExample.vue?raw'

export const panelConfig = {
  value: {
    type: 'boolean' as const,
    title: 'value',
    initialState: false,
    help: 'The checked state of the cell. Bound via v-model.'
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

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import CheckboxCell from '@/monitoring/shared/components/cell/CheckboxCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: '_',
    minSize: 25,
    maxSize: 25
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CheckboxCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-checkbox-cell__table-wrap">
        <MonitoringTable
          :rows="rows"
          :loading="false"
          :has-loaded="true"
          :columns="columns"
          :sort-state="sortState"
          :filter-state="filterState"
          @update:sort-state="sortState = $event"
          @update:filter-state="filterState = $event"
        >
          <template #row>
            <CheckboxCell v-model="propState.value" />
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
.ucl-checkbox-cell__table-wrap {
  width: 100%;
}

/* The demo has a single sized column. MonitoringTable stretches its table to
   width: 100%, which (with table-layout: fixed) would spread the slack onto that
   lone column and hide its size. Let the table size to its columns instead. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.ucl-checkbox-cell__table-wrap :deep(.monitoring-table__table) {
  width: auto;
}
</style>
