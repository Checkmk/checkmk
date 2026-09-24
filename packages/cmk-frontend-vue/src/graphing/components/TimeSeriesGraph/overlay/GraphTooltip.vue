<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'
import CmkPointerTooltip from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import { computed } from 'vue'

import { isoDate, isoTime, shortWeekday } from '../../../utils/timeFormat'
import MetricAttributeGroups from '../../MetricAttributeGroups.vue'
import type { HoverState } from '../interaction/hover'

const props = defineProps<{
  hoverState: HoverState | null
}>()

// Only the hovered line's; every line's would outgrow the tooltip.
const closestSample = computed(() =>
  props.hoverState?.samples.find((sample) => sample.isClosest && sample.attributes.length > 0)
)

const formattedTime = computed(() => {
  if (!props.hoverState) {
    return ''
  }
  const timeZone = getLocalTimeZone()
  const zonedTime = fromAbsolute(props.hoverState.snapTime * 1000, timeZone)
  return `${shortWeekday(props.hoverState.snapTime, timeZone)}, ${isoDate(zonedTime)}  ${isoTime(zonedTime)}`
})
</script>

<template>
  <CmkPointerTooltip :pointer="hoverState">
    <div v-if="hoverState" class="graphing-graph-tooltip">
      <div class="graphing-graph-tooltip__time">{{ formattedTime }}</div>
      <div class="graphing-graph-tooltip__rows">
        <div
          v-for="sample in hoverState.samples"
          :key="sample.metricName"
          class="graphing-graph-tooltip__row"
          :class="{ 'graphing-graph-tooltip__row--is-closest': sample.isClosest }"
        >
          <span class="graphing-graph-tooltip__swatch" :style="{ background: sample.color }" />
          <span class="graphing-graph-tooltip__label">{{ sample.label }}</span>
          <span class="graphing-graph-tooltip__value">{{ sample.formattedValue }}</span>
        </div>
      </div>
      <MetricAttributeGroups
        v-if="closestSample"
        class="graphing-graph-tooltip__attributes"
        :attributes="closestSample.attributes"
      />
    </div>
  </CmkPointerTooltip>
</template>

<style scoped>
.graphing-graph-tooltip {
  min-width: 280px;
  max-width: 420px;
}

.graphing-graph-tooltip__time {
  margin-bottom: var(--spacing);
  padding: var(--spacing-half) 8px;
  font-variant-numeric: tabular-nums;
}

.graphing-graph-tooltip__rows {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.graphing-graph-tooltip__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--spacing-half) 8px;
  border-radius: var(--border-radius);
}

.graphing-graph-tooltip__row--is-closest {
  background: color-mix(in srgb, var(--font-color) 10%, transparent);
}

.graphing-graph-tooltip__swatch {
  flex: 0 0 auto;
  width: 4px;
  height: 16px;
  border-radius: var(--border-radius-half);
}

.graphing-graph-tooltip__label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-graph-tooltip__value {
  flex: 0 0 auto;
  padding-left: var(--spacing);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.graphing-graph-tooltip__attributes {
  margin-top: var(--spacing);
  padding: var(--spacing) 8px 0;
  border-top: 1px solid var(--ux-theme-6);
}
</style>
