<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'

import codeExample from './UclStringCellCodeExample.vue?raw'

type LinkTarget = CellLink['target']
type LinkVariant = NonNullable<CellLink['variant']>

const LINK_TARGET_OPTIONS: Options<NonNullable<LinkTarget>>[] = [
  { title: 'Self', name: '_self' },
  { title: 'Blank', name: '_blank' }
]

const LINK_VARIANT_OPTIONS: Options<LinkVariant>[] = [
  { title: 'Inline', name: 'inline' },
  { title: 'Icon', name: 'icon' }
]

export const panelConfig = {
  value: {
    type: 'string' as const,
    title: 'value',
    initialState:
      'example.host.checkmk.com / Filesystem /var/log — long_descriptive_label_that_keeps_going',
    help: 'The text rendered inside the cell. Line breaks are allowed after spaces, hyphens, underscores and dots.'
  },
  hardBreakEvery: {
    type: 'number' as const,
    title: 'hardBreakEvery',
    initialState: 15,
    help: 'Fallback break opportunity inserted every N characters when no natural separators are available.'
  },
  linkEnabled: {
    type: 'boolean' as const,
    title: 'linkedTo',
    initialState: true,
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
    options: LINK_TARGET_OPTIONS,
    initialState: '_blank' as const
  },
  linkVariant: {
    type: 'list' as const,
    title: '↳ variant',
    options: LINK_VARIANT_OPTIONS,
    initialState: 'icon' as const
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
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const SLIDER_MIN = 60
const SLIDER_MAX = 600

const sliderValue = ref<number>(200)

/** Slider width clamped by the configured min/max column width. */
const effectiveCellWidth = computed(() =>
  Math.min(Math.max(sliderValue.value, propState.value.minWidth), propState.value.maxWidth)
)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

// The slider-driven container (with its CSS min/max-width) is what sizes this
// demo. The column stays flexible so the table fills the container's padded
// content box instead of overflowing it (table-layout: fixed would otherwise
// expand the table to the explicit column width and clip past the padding).
const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Value'
  }
])

const linkedTo = computed<CellLink | undefined>(() =>
  propState.value.linkEnabled
    ? {
        href: propState.value.linkHref,
        target: propState.value.linkTarget,
        variant: propState.value.linkVariant
      }
    : undefined
)

const LINK_SUB_KEYS = ['linkHref', 'linkTarget', 'linkVariant'] as const

const visibleConfig = computed(() =>
  Object.fromEntries(
    Object.entries(panelConfig).filter(([key]) => {
      if (!propState.value.linkEnabled && (LINK_SUB_KEYS as readonly string[]).includes(key)) {
        return false
      }
      return true
    })
  )
)

const sliderFillPercent = computed(
  () => ((sliderValue.value - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN)) * 100
)

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

const currentWidth = computed(() => `${effectiveCellWidth.value} px`)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>StringCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-string-cell__stack">
        <div class="ucl-string-cell__slider-controls">
          <div class="ucl-string-cell__slider-header">
            <span class="ucl-string-cell__slider-label">Cell width</span>
            <span class="ucl-string-cell__current-width">
              <strong>{{ currentWidth }}</strong>
            </span>
          </div>
          <input
            v-model.number="sliderValue"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ background: sliderTrackBackground }"
            class="ucl-string-cell__slider"
          />
        </div>

        <div
          class="ucl-string-cell__container"
          :style="{
            width: `${sliderValue}px`,
            minWidth: `${propState.minWidth}px`,
            maxWidth: `${propState.maxWidth}px`
          }"
        >
          <MonitoringTable
            :rows="rows"
            :loading="false"
            :columns="columns"
            :sort-state="sortState"
            :filter-state="filterState"
            @update:sort-state="sortState = $event"
            @update:filter-state="filterState = $event"
          >
            <template #row>
              <StringCell
                :value="propState.value"
                :hard-break-every="propState.hardBreakEvery"
                :linked-to="linkedTo"
              />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-string-cell__hint">
          Drag the slider to change the cell width. The cell clamps at three lines and breaks
          preferentially at spaces, hyphens, underscores and dots; longer unbroken runs fall back to
          <code>hardBreakEvery</code>.
        </p>
      </div>

      <template #properties>
        <div class="ucl-string-cell__panel">
          <UclPropertiesPanel v-model="propState" :config="visibleConfig" />
        </div>
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-string-cell__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  min-width: 0;
}

.ucl-string-cell__slider-controls {
  width: 100%;
}

.ucl-string-cell__slider-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-string-cell__slider-label {
  font-weight: var(--font-weight-bold);
}

.ucl-string-cell__current-width {
  font-style: italic;
  opacity: 0.7;
}

.ucl-string-cell__slider {
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

.ucl-string-cell__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-string-cell__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-string-cell__container {
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  margin-left: calc(-1 * var(--dimension-4));
  overflow: hidden;
}

.ucl-string-cell__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-string-cell__panel :deep(div:has(> div > label[for$='-linkHref'])),
.ucl-string-cell__panel :deep(div:has(> div > label[for$='-linkTarget'])),
.ucl-string-cell__panel :deep(div:has(> div > label[for$='-linkVariant'])) {
  padding-left: 16px;
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
