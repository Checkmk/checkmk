<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclLabelCellCodeExample.vue?raw'

export const panelConfig = {
  count: {
    type: 'number' as const,
    title: 'count',
    initialState: 6,
    help: 'Number of entries to render. Only the ones fitting the cell width are shown.'
  },
  color: {
    type: 'list' as const,
    title: 'color',
    options: [
      { title: 'discovered', name: 'discovered' },
      { title: 'explicit', name: 'explicit' },
      { title: 'ruleset', name: 'ruleset' },
      { title: 'default', name: 'default' },
      { title: 'success', name: 'success' }
    ],
    initialState: 'discovered',
    help: 'Tag color, e.g. the label source a monitoring page maps onto it.'
  },
  variant: {
    type: 'list' as const,
    title: 'variant',
    options: [
      { title: 'fill', name: 'fill' },
      { title: 'outline', name: 'outline' },
      { title: 'weighted', name: 'weighted' }
    ],
    initialState: 'fill',
    help: 'Tag variant.'
  },
  size: {
    type: 'list' as const,
    title: 'size',
    options: [
      { title: 'small', name: 'small' },
      { title: 'medium', name: 'medium' },
      { title: 'large', name: 'large' }
    ],
    initialState: 'small',
    help: 'Tag size.'
  },
  longEntry: {
    type: 'boolean' as const,
    title: 'longEntry',
    initialState: false,
    help: 'Make the first entry wider than the cell, so it is ellipsised with a full-text tooltip.'
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
import type { Colors, Sizes, Variants } from 'cmk-ui-library/components/CmkTag.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { TABLE_BORDER_SPACING } from '@/monitoring/shared/components/MonitoringTableContext'
import LabelCell, { type LabelCellItem } from '@/monitoring/shared/components/cell/LabelCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const LONG_ENTRY = 'cmk/azure/resource_group: a-very-long-resource-group-name'

const items = computed<LabelCellItem[]>(() =>
  Array.from({ length: Math.max(0, propState.value.count) }, (_unused, index) => ({
    text: (index === 0 && propState.value.longEntry
      ? LONG_ENTRY
      : `cmk/label_${index + 1}: value_${index + 1}`) as TranslatedString,
    color: propState.value.color as Colors,
    variant: propState.value.variant as Variants
  }))
)

const size = computed<Sizes>(() => propState.value.size as Sizes)

const SLIDER_MIN = 100
const SLIDER_MAX = 700

const sliderValue = ref<number>(280)

const COLUMN_MIN = 100
const COLUMN_MAX = 700

const effectiveWidth = computed(() => Math.min(Math.max(sliderValue.value, COLUMN_MIN), COLUMN_MAX))

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Labels',
    size: sliderValue.value,
    minSize: COLUMN_MIN,
    maxSize: COLUMN_MAX
  }
])

const sliderFillPercent = computed(
  () => ((sliderValue.value - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN)) * 100
)

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

const currentWidth = computed(() => `${effectiveWidth.value} px`)
// The table lays its column out inside a border-spacing on either side; without that slack the
// table is wider than the box and the demo grows a horizontal scrollbar.
const containerWidth = computed(() => `${effectiveWidth.value + 2 * TABLE_BORDER_SPACING}px`)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>LabelCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-label-cell__stack">
        <div class="ucl-label-cell__slider-controls">
          <div class="ucl-label-cell__slider-header">
            <span class="ucl-label-cell__slider-label">Cell width</span>
            <span class="ucl-label-cell__current-width">
              <strong>{{ currentWidth }}</strong>
            </span>
          </div>
          <input
            v-model.number="sliderValue"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ background: sliderTrackBackground }"
            class="ucl-label-cell__slider"
          />
        </div>

        <div class="ucl-label-cell__container">
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
              <LabelCell column-id="cell" :items="items" :size="size" />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-label-cell__hint">
          Drag the slider to change the cell width. Entries that no longer fit collapse into the
          "+X" button; pressing it shows all of them.
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
.ucl-label-cell__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  min-width: 0;
}

.ucl-label-cell__slider-controls {
  width: 100%;
}

.ucl-label-cell__slider-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-label-cell__slider-label {
  font-weight: var(--font-weight-bold);
}

.ucl-label-cell__current-width {
  font-style: italic;
  opacity: 0.7;
}

.ucl-label-cell__slider {
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

.ucl-label-cell__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-label-cell__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

/* The slider drives the box's content width, which is what the cell measures itself against.
   Sizing the table to the column instead would let the cell's own content widen it. */
.ucl-label-cell__container {
  width: v-bind(containerWidth);
  max-width: 100%;
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: content-box;
  margin-left: calc(-1 * var(--dimension-4));
  overflow: hidden;
}

.ucl-label-cell__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
