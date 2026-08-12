<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclColumnPicker.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'The toolbar control is a cog icon button with aria-haspopup / aria-expanded, reachable in the natural tab order (accessible name "Show or hide columns").'
  },
  {
    keys: ['↑', '↓'],
    description:
      'While the popover is open, arrow keys move between the focusable rows: the search field, each column toggle, and the "Back to default" / Apply / Cancel buttons.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Toggle the focused column between shown and hidden. Each toggle is a button exposing the column name and its on/off state (aria-pressed) to assistive tech.'
  },
  {
    keys: ['Esc'],
    description:
      'Clears the search field if it has text, otherwise closes the popover and returns focus to the trigger.'
  }
]

export const panelConfig = {
  columnSet: {
    type: 'list' as const,
    title: 'Column count',
    options: [
      { name: 'few', title: 'Few columns' },
      { name: 'many', title: 'Many columns (scrolls)' }
    ],
    initialState: 'few',
    help: 'The toggle list scrolls once it exceeds the popover height; the search field filters it regardless of count.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import type { VisibilityState } from '@tanstack/vue-table'
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, provide, ref, watch } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import type { ToggleableColumn } from '@/monitoring/shared/tableState/schema'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const FEW_COLUMNS: { id: string; label: string; hidden?: boolean }[] = [
  { id: 'address', label: 'IP address' },
  { id: 'alias', label: 'Alias', hidden: true },
  { id: 'services', label: 'Services' },
  { id: 'notifications', label: 'Notifications', hidden: true }
]

const MANY_COLUMNS = [
  ...FEW_COLUMNS,
  { id: 'contacts', label: 'Contacts', hidden: true },
  { id: 'labels', label: 'Labels', hidden: true },
  { id: 'parents', label: 'Parents', hidden: true },
  { id: 'site', label: 'Site' },
  { id: 'perfometer', label: 'Perf-O-Meter' },
  { id: 'last_check', label: 'Last check', hidden: true },
  { id: 'check_age', label: 'Check age', hidden: true },
  { id: 'comments', label: 'Comments', hidden: true }
]

const activeColumns = computed(() =>
  propState.value.columnSet === 'many' ? MANY_COLUMNS : FEW_COLUMNS
)

const toggleableColumns = computed<ToggleableColumn[]>(() =>
  activeColumns.value.map((column) => ({ id: column.id, label: untranslated(column.label) }))
)

function defaultVisibility(): VisibilityState {
  const visibility: VisibilityState = {}
  for (const column of activeColumns.value) {
    if (column.hidden) {
      visibility[column.id] = false
    }
  }
  return visibility
}

const columnVisibility = ref<VisibilityState>(defaultVisibility())

watch(
  () => propState.value.columnSet,
  () => {
    columnVisibility.value = defaultVisibility()
  }
)

const demoService = {
  get toggleableColumns() {
    return toggleableColumns.value
  },
  columnVisibility,
  get defaultColumnVisibility() {
    return defaultVisibility()
  },
  updateColumnVisibility(next: VisibilityState) {
    columnVisibility.value = next
  },
  resetColumnVisibility() {
    columnVisibility.value = defaultVisibility()
  },
  beginAutoPause() {},
  endAutoPause() {}
}

provide(MONITORING_SERVICE, demoService as unknown as MonitoringService<unknown>)

const visibleColumns = computed(() =>
  toggleableColumns.value
    .filter((column) => columnVisibility.value[column.id] !== false)
    .map((column) => column.label)
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Column picker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-column-picker__stack">
        <div class="ucl-column-picker__toolbar">
          <ColumnPicker />
        </div>

        <p class="ucl-column-picker__readout">
          Visible columns:
          <code v-if="visibleColumns.length">{{ visibleColumns.join(' · ') }}</code>
          <span v-else>none</span>
        </p>

        <p class="ucl-column-picker__hint">
          The cog control reuses the <code>FilterDropdown</code> popover (the same shell as the
          column filters) with a new <code>column-visibility</code> content: an eye / eye-slashed
          list of the toggleable columns plus a search field. Toggles are staged in the dropdown's
          draft and only written to the injected MonitoringService (<code>toggleableColumns</code> /
          <code>columnVisibility</code>) on Apply; Cancel, click-outside and Escape discard them.
          "Back to default" restores the column set defined by each column's
          <code>meta.hidden</code> flag. Wiring this into a real table (default set, fixed columns,
          persistence) is done by the consuming view.
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
.ucl-column-picker__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-column-picker__toolbar {
  display: flex;
  justify-content: flex-end;
  padding: var(--dimension-4);
  background: var(--ux-theme-2);
  border-radius: 4px;
}

.ucl-column-picker__readout,
.ucl-column-picker__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
