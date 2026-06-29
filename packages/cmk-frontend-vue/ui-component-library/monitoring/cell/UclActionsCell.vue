<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclActionsCellCodeExample.vue?raw'

export const panelConfig = {
  maxVisible: {
    type: 'number' as const,
    title: 'maxVisible',
    initialState: 2,
    help: 'How many actions are shown directly as icon buttons. The rest move into the "show more" dropdown.'
  },
  actionCount: {
    type: 'number' as const,
    title: 'actions',
    initialState: 4,
    help: 'Number of actions provided to the cell (capped at the demo set).'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import type { ColumnDef, ColumnFiltersState } from '@tanstack/vue-table'
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import ActionsCell, { type CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const ALL_ACTIONS: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' },
  { id: 'downtime', label: 'Schedule downtime' as TranslatedString, icon: 'downtime' },
  { id: 'comment', label: 'Add comment' as TranslatedString, icon: 'comment' },
  {
    id: 'notifications',
    label: 'Disable notifications' as TranslatedString,
    icon: 'notif-disabled'
  }
]

const actions = computed<CellAction[]>(() =>
  ALL_ACTIONS.slice(0, Math.max(0, Math.min(propState.value.actionCount, ALL_ACTIONS.length)))
)

const lastSelected = ref<string | null>(null)

function onSelect(action: CellAction): void {
  lastSelected.value = action.id
}

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Actions',
    minSize: 120,
    maxSize: 240,
    meta: { justify: 'right' }
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>ActionsCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-actions-cell__stack">
        <div class="ucl-actions-cell__container">
          <MonitoringTable
            :rows="rows"
            :fetch-state="'idle'"
            :has-loaded="true"
            :columns="columns"
            :filter-state="filterState"
            @update:filter-state="filterState = $event"
          >
            <template #row>
              <ActionsCell
                column-id="cell"
                :actions="actions"
                :max-visible="propState.maxVisible"
                @select="onSelect"
              />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-actions-cell__hint">
          The first <code>{{ propState.maxVisible }}</code> action(s) render as icon buttons; the
          remaining {{ Math.max(0, actions.length - propState.maxVisible) }} appear in the
          <code>show more</code> dropdown. Last selected action:
          <strong>{{ lastSelected ?? '—' }}</strong>
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-actions-cell__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  min-width: 0;
}

.ucl-actions-cell__container {
  width: fit-content;
  max-width: 100%;
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  overflow: visible;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.ucl-actions-cell__container :deep(.monitoring-table__table) {
  width: auto;
}

.ucl-actions-cell__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
