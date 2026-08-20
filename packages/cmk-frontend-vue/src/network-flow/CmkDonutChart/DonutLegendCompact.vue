<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import GraphLegendEyeButton from '@/graphing/components/legend/GraphLegendEyeButton.vue'

import { chartColorCss } from '../colors'
import type { DonutLegendRow } from './types'

const { _t } = usei18n()

defineProps<{
  rows: DonutLegendRow[]
  highlighted: string | null
}>()

// No drill: the chips carry no chevron for the remainder either, because at
// this size a second control per chip is what pushes the names back out of
// view. A reader who wants the breakdown has the table.
defineEmits<{
  toggle: [key: string]
  highlight: [key: string | null]
}>()
</script>

<template>
  <!-- Names only: at this size a number would take the width the name needs,
       and the volume is one hover away in the center of the ring. -->
  <CmkScrollContainer
    class="network-flow-donut-legend-compact"
    max-height="100%"
    height="auto"
    :style="{ overflowX: 'hidden' }"
  >
    <ul class="network-flow-donut-legend-compact__chips">
      <li
        v-for="row in rows"
        :key="row.key"
        class="network-flow-donut-legend-compact__chip"
        :class="{
          'network-flow-donut-legend-compact__chip--highlighted': highlighted === row.key,
          'network-flow-donut-legend-compact__chip--hidden': row.hidden
        }"
        @mouseenter="$emit('highlight', row.key)"
        @mouseleave="$emit('highlight', null)"
      >
        <!-- Wrapped, so the fixed-size button is not the part that gives way
             when a chip has to shrink. -->
        <span class="network-flow-donut-legend-compact__eye">
          <GraphLegendEyeButton
            :hidden="row.hidden"
            :aria-label="
              row.hidden
                ? _t('Show %{category} in the chart', { category: row.label })
                : _t('Hide %{category} in the chart', { category: row.label })
            "
            @toggle="$emit('toggle', row.key)"
          />
        </span>
        <span
          class="network-flow-donut-legend-compact__swatch"
          :style="{ backgroundColor: row.hidden ? '' : chartColorCss(row.color) }"
        />
        <span class="network-flow-donut-legend-compact__label" :title="row.label">
          {{ row.label }}
        </span>
      </li>
    </ul>
  </CmkScrollContainer>
</template>

<style scoped>
/* Below the ring, so it takes the width and gives back the height. */
.network-flow-donut-legend-compact {
  flex: 0 1 auto;
  width: 100%;
  min-height: 0;
}

.network-flow-donut-legend-compact__chips {
  display: flex;
  flex-wrap: wrap;
  gap: clamp(2px, 1cqh, 6px);
  justify-content: center;
  padding: 0;
  margin: 0;
  list-style: none;
}

.network-flow-donut-legend-compact__chip {
  display: flex;
  flex: 0 1 auto;
  gap: 2px;
  align-items: center;
  min-width: 0;
  padding: 2px 4px;
  border-radius: var(--border-radius);
}

.network-flow-donut-legend-compact__eye {
  display: flex;
  flex: 0 0 auto;
}

.network-flow-donut-legend-compact__chip--highlighted {
  background-color: var(--ux-theme-4);
}

/* A hidden category keeps its chip, so it stays reachable. */
.network-flow-donut-legend-compact__chip--hidden {
  opacity: 0.45;
}

.network-flow-donut-legend-compact__swatch {
  flex: 0 0 auto;
  width: 0.3em;
  min-width: 3px;
  height: 1.1em;
  border-radius: var(--border-radius-half);
}

.network-flow-donut-legend-compact__chip--hidden .network-flow-donut-legend-compact__swatch {
  background-color: var(--color-mid-grey-30);
}

.network-flow-donut-legend-compact__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
