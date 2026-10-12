<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { HostOrServiceState, VisualContext } from '@/dashboard/types/widget'

import {
  HOST_OR_SERVICE_STATE_COLOR,
  hostOrServiceStateKind,
  shortHostOrServiceState
} from './lib/hostOrServiceState'
import { valueFontSize } from './lib/valueFontSize'

const props = defineProps<{
  value: HostOrServiceState
  width: number
  height: number
  filters: VisualContext
}>()

const SUMMARY_MARGIN = 15
const SUMMARY_FONT_SIZE = 14

const stateKind = computed(() =>
  hostOrServiceStateKind(props.value.state, props.value.has_been_checked)
)

const fontSizePx = computed(() => `${valueFontSize(props.width, props.height)}px`)

const summaryBox = computed(() => ({
  x: SUMMARY_MARGIN,
  y: props.height / 2 + 2 * SUMMARY_FONT_SIZE,
  width: Math.max(0, props.width - 2 * SUMMARY_MARGIN),
  height: Math.max(0, props.height / 2 - 4 * SUMMARY_FONT_SIZE)
}))
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-state-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <rect
      v-if="value.tint_background"
      class="db-cmk-state-figure__background"
      :width="width"
      :height="height"
      :fill="HOST_OR_SERVICE_STATE_COLOR[stateKind]"
      aria-hidden="true"
    />
    <ContextualLinkTrigger
      :links="value.links"
      :link-properties="value.link_properties"
      :filters="filters"
    >
      <foreignObject
        v-if="value.plugin_output !== null"
        class="db-cmk-state-figure__summary-box"
        :x="summaryBox.x"
        :y="summaryBox.y"
        :width="summaryBox.width"
        :height="summaryBox.height"
      >
        <div class="db-cmk-state-figure__summary">{{ value.plugin_output }}</div>
      </foreignObject>
      <text
        class="db-cmk-state-figure__state"
        :x="width / 2"
        :y="height / 2"
        text-anchor="middle"
        dominant-baseline="central"
      >
        {{ shortHostOrServiceState(stateKind) }}
      </text>
    </ContextualLinkTrigger>
  </svg>
</template>

<style scoped>
.db-cmk-state-figure {
  display: block;
}

.db-cmk-state-figure__background {
  opacity: 0.6;
}

.db-cmk-state-figure__summary-box {
  position: relative;
}

.db-cmk-state-figure__summary {
  position: absolute;
  bottom: 0;
  width: 100%;
  color: var(--font-color);
  font-size: 14px;
  text-align: center;
  overflow-wrap: break-word;
}

.db-cmk-state-figure__state {
  fill: var(--font-color);
  font-size: v-bind(fontSizePx);
  font-weight: bold;
}
</style>
