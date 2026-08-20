<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclNumberCellCodeExample.vue?raw'

export const panelConfig = {
  value: {
    type: 'number' as const,
    title: 'value',
    initialState: 42,
    help: 'The numeric value rendered inside the cell.'
  },
  decimals: {
    type: 'number' as const,
    title: 'decimals',
    initialState: 0,
    help: 'Number of decimal places passed to value.toFixed(). Defaults to 0.'
  },
  linkEnabled: {
    type: 'boolean' as const,
    title: 'linkedTo',
    initialState: false,
    help: 'Wrap the cell content in an <a> tag.'
  },
  linkHref: {
    type: 'string' as const,
    title: '↳ href',
    initialState: 'https://checkmk.com'
  },
  linkTarget: {
    type: 'list' as const,
    title: '↳ target',
    options: [
      { title: '_self', name: '_self' },
      { title: '_blank', name: '_blank' }
    ],
    initialState: '_self'
  },
  linkVariant: {
    type: 'list' as const,
    title: '↳ variant',
    options: [
      { title: 'inline', name: 'inline' },
      { title: 'icon', name: 'icon' }
    ],
    initialState: 'inline'
  },
  highlightEnabled: {
    type: 'boolean' as const,
    title: 'highlight',
    initialState: false,
    help: 'Colour the value and mark it with an accent bar instead of plain text.'
  },
  highlightColor: {
    type: 'list' as const,
    title: '↳ color',
    options: [
      { title: 'default', name: 'default' },
      { title: 'success', name: 'success' },
      { title: 'warning', name: 'warning' },
      { title: 'danger', name: 'danger' },
      { title: 'unknown', name: 'unknown' },
      { title: 'pending', name: 'pending' }
    ],
    initialState: 'default'
  },
  highlightMinWidth: {
    type: 'number' as const,
    title: '↳ minWidth',
    initialState: 0,
    help: 'Minimum width in px applied to the value. 0 leaves it unset.'
  },
  minWidth: {
    type: 'number' as const,
    title: 'minWidth',
    initialState: 60,
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

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { ColumnJustify } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'
import NumberCell from '@/monitoring/shared/components/cell/NumberCell.vue'
import type { CellHighlight } from '@/monitoring/shared/components/cell/base/highlight'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const linkedTo = computed<CellLink | undefined>(() =>
  propState.value.linkEnabled
    ? {
        href: propState.value.linkHref,
        target: propState.value.linkTarget,
        variant: propState.value.linkVariant as CellLink['variant']
      }
    : undefined
)

const highlight = computed<CellHighlight | undefined>(() =>
  propState.value.highlightEnabled
    ? {
        color: propState.value.highlightColor as CellHighlight['color'],
        minWidth: propState.value.highlightMinWidth || undefined
      }
    : undefined
)

const justify = computed<ColumnJustify>(() => propState.value.justify as ColumnJustify)

const LINK_SUB_KEYS = ['linkHref', 'linkTarget', 'linkVariant'] as const
const HIGHLIGHT_SUB_KEYS = ['highlightColor', 'highlightMinWidth'] as const

const visibleConfig = computed(() =>
  Object.fromEntries(
    Object.entries(panelConfig).filter(([key]) => {
      if (!propState.value.linkEnabled && (LINK_SUB_KEYS as readonly string[]).includes(key)) {
        return false
      }
      if (
        !propState.value.highlightEnabled &&
        (HIGHLIGHT_SUB_KEYS as readonly string[]).includes(key)
      ) {
        return false
      }
      return true
    })
  )
)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Value',
    minSize: propState.value.minWidth,
    maxSize: propState.value.maxWidth,
    meta: { justify: justify.value }
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>NumberCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-number-cell__table-wrap">
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
            <NumberCell
              column-id="cell"
              :value="propState.value"
              :decimals="propState.decimals"
              :highlight="highlight"
              :linked-to="linkedTo"
            />
          </template>
        </MonitoringTable>
      </div>

      <template #properties>
        <UclPropertiesPanel
          v-model="propState"
          :config="visibleConfig"
          class="ucl-number-cell__panel"
        />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-number-cell__table-wrap {
  width: 100%;
}

/* The demo has a single sized column. MonitoringTable stretches its table to
   width: 100%, which (with table-layout: fixed) would spread the slack onto that
   lone column and hide its size. Let the table size to its columns instead. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.ucl-number-cell__table-wrap :deep(.monitoring-table__table) {
  width: auto;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-number-cell__panel :deep(div:has(> div > label[for$='-linkHref'])),
.ucl-number-cell__panel :deep(div:has(> div > label[for$='-linkTarget'])),
.ucl-number-cell__panel :deep(div:has(> div > label[for$='-linkVariant'])),
.ucl-number-cell__panel :deep(div:has(> div > label[for$='-highlightColor'])),
.ucl-number-cell__panel :deep(div:has(> div > label[for$='-highlightMinWidth'])) {
  padding-left: 16px;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
