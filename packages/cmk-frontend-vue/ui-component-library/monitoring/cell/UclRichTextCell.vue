<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclRichTextCellCodeExample.vue?raw'

type Content = 'text' | 'nested'

const CONTENT_OPTIONS: Options<Content>[] = [
  { title: 'text (value)', name: 'text' },
  { title: 'nested components (slot)', name: 'nested' }
]

export const panelConfig = {
  content: {
    type: 'list' as const,
    title: 'content',
    options: CONTENT_OPTIONS,
    initialState: 'nested' as Content,
    help: 'Render a plain text value or nested components passed through the default slot.'
  },
  value: {
    type: 'string' as const,
    title: 'value',
    initialState:
      'example.host.checkmk.com / Filesystem /var/log — long_descriptive_label_that_keeps_going',
    help: 'The text rendered when content is "text". Long values wrap at the cell edge.'
  },
  minWidth: {
    type: 'number' as const,
    title: 'minWidth',
    initialState: 150,
    help: 'Minimum column width in px (tanstack column minSize). Clamps the slider.'
  },
  maxWidth: {
    type: 'number' as const,
    title: 'maxWidth',
    initialState: 600,
    help: 'Maximum column width in px (tanstack column maxSize). Clamps the slider.'
  },
  justify: {
    type: 'list' as const,
    title: 'justify',
    options: [
      { title: 'left', name: 'left' as const },
      { title: 'center', name: 'center' as const },
      { title: 'right', name: 'right' as const }
    ],
    initialState: 'left' as const,
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
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import { computed, ref } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { ColumnJustify } from '@/monitoring/shared/components/MonitoringTableContext'
import RichTextCell from '@/monitoring/shared/components/cell/RichTextCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const justify = computed<ColumnJustify>(() => propState.value.justify as ColumnJustify)

const SLIDER_MIN = 60
const SLIDER_MAX = 600

const sliderValue = ref<number>(300)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Service summary',
    meta: { justify: justify.value }
  }
])

const sliderFillPercent = computed(
  () => ((sliderValue.value - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN)) * 100
)

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

const currentWidth = computed(() => `${sliderValue.value} px`)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>RichTextCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-rich-text-cell__stack">
        <div class="ucl-rich-text-cell__slider-controls">
          <div class="ucl-rich-text-cell__slider-header">
            <span class="ucl-rich-text-cell__slider-label">Cell width</span>
            <span class="ucl-rich-text-cell__current-width">
              <strong>{{ currentWidth }}</strong>
            </span>
          </div>
          <input
            v-model.number="sliderValue"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ background: sliderTrackBackground }"
            class="ucl-rich-text-cell__slider"
          />
        </div>

        <div
          class="ucl-rich-text-cell__container"
          :style="{
            width: `${sliderValue}px`,
            minWidth: `${propState.minWidth}px`,
            maxWidth: `${propState.maxWidth}px`
          }"
        >
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
              <RichTextCell
                v-if="propState.content === 'text'"
                column-id="cell"
                :value="propState.value"
              />
              <RichTextCell v-else column-id="cell">
                <CmkTag color="danger" variant="weighted" content="CRIT" size="small" />
                CPU utilization is 95% —
                <a href="https://checkmk.com" target="_blank">view graph</a>
              </RichTextCell>
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-rich-text-cell__hint">
          Like the StringCell, the cell clamps at three lines. With <code>content: nested</code> the
          default slot lets you nest arbitrary components (tags, links, icons) inside that clamped
          region.
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
.ucl-rich-text-cell__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  min-width: 0;
}

.ucl-rich-text-cell__slider-controls {
  width: 100%;
}

.ucl-rich-text-cell__slider-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-rich-text-cell__slider-label {
  font-weight: var(--font-weight-bold);
}

.ucl-rich-text-cell__current-width {
  font-style: italic;
  opacity: 0.7;
}

.ucl-rich-text-cell__slider {
  appearance: none;
  display: block;
  width: 100%;
  height: 6px;
  margin: var(--dimension-6) 0 var(--dimension-4) 0;
  padding: 0;
  background: var(--ux-theme-6);
  border-radius: 3px;
  cursor: pointer;
}

.ucl-rich-text-cell__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-rich-text-cell__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-rich-text-cell__container {
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  margin-left: calc(-1 * var(--dimension-4));
  overflow: hidden;
}

.ucl-rich-text-cell__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
