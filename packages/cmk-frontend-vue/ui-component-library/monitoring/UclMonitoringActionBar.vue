<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const panelConfig = {
  selectedCount: {
    type: 'number' as const,
    title: 'selectedCount',
    initialState: 2,
    help: 'Number of currently selected hosts. The bar is disabled while this is 0.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

import codeExample from './UclMonitoringActionBarCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const actions: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' },
  { id: 'downtime', label: 'Schedule downtime' as TranslatedString, icon: 'downtime' }
]

const lastAction = ref<string | null>(null)

function onAction(action: CellAction): void {
  lastAction.value = action.id
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>MonitoringActionBar</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-monitoring-action-bar__stack">
        <MonitoringActionBar
          :selected-count="propState.selectedCount"
          :actions="actions"
          @action="onAction"
        />

        <p class="ucl-monitoring-action-bar__hint">
          The contextual action bar for the selected hosts. It stays visible but is disabled while
          no host is selected. Last triggered action: <strong>{{ lastAction ?? '—' }}</strong>
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
.ucl-monitoring-action-bar__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  max-width: 640px;
}

.ucl-monitoring-action-bar__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
