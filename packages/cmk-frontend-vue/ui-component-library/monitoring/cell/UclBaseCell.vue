<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclBaseCellCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['—'],
    description:
      "Without the button prop the cell renders a plain <td> and inherits the table's keyboard semantics."
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'With the button prop the cell renders a native <button>, is keyboard focusable, and activates on Enter/Space, emitting a click event.'
  }
]

export const panelConfig = {
  defaultContent: {
    type: 'string' as const,
    title: 'default slot',
    initialState: 'host-01.example.com',
    help: 'Content rendered into the cell when no breakpoints are configured.'
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
    help: 'Align the cell content.'
  },
  buttonEnabled: {
    type: 'boolean' as const,
    title: 'button',
    initialState: false,
    help: 'Render the cell as a <button> with a trailing chevron; a click emits an event.'
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
    help: 'Colour the cell value and mark it with an accent bar.'
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
    help: 'Minimum width of the highlight in pixels (0 disables it).'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
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

const justify = computed(() => propState.value.justify as 'left' | 'center' | 'right')

const highlight = computed<CellHighlight | undefined>(() =>
  propState.value.highlightEnabled
    ? {
        color: propState.value.highlightColor as CellHighlight['color'],
        minWidth:
          propState.value.highlightMinWidth > 0 ? propState.value.highlightMinWidth : undefined
      }
    : undefined
)

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
    header: 'Cell',
    size: 320,
    maxSize: 360
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>BaseCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-base-cell__table-wrap">
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
            <BaseCell
              :linked-to="linkedTo"
              :highlight="highlight"
              :justify="justify"
              :button="propState.buttonEnabled"
            >
              {{ propState.defaultContent }}
            </BaseCell>
          </template>
        </MonitoringTable>
      </div>

      <template #properties>
        <UclPropertiesPanel
          v-model="propState"
          :config="visibleConfig"
          class="ucl-base-cell__panel"
        />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-base-cell__table-wrap {
  width: 100%;
}

/* The demo has a single sized column. MonitoringTable stretches its table to
   width: 100%, which (with table-layout: fixed) would spread the slack onto that
   lone column and hide its size. Let the table size to its columns instead. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.ucl-base-cell__table-wrap :deep(.monitoring-table__table) {
  width: auto;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkHref'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkTarget'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-linkVariant'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-highlightColor'])),
.ucl-base-cell__panel :deep(div:has(> div > label[for$='-highlightMinWidth'])) {
  padding-left: 16px;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
