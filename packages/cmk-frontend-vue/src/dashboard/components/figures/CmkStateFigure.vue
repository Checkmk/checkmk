<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { ObjectState, VisualContext } from '@/dashboard/types/widget'

import { valueFontSize } from './lib/valueFontSize'

const props = defineProps<{
  value: ObjectState
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const { _t } = usei18n()

const SUMMARY_MARGIN = 15
const SUMMARY_FONT_SIZE = 14

type StateKind = ObjectState['state'] | 'PENDING'

const STATE_COLOR: Record<StateKind, string> = {
  UP: 'var(--color-state-ok)',
  OK: 'var(--color-state-ok)',
  WARNING: 'var(--color-state-warning)',
  DOWN: 'var(--color-state-critical)',
  CRITICAL: 'var(--color-state-critical)',
  UNREACHABLE: 'var(--color-state-unknown)',
  UNKNOWN: 'var(--color-state-unknown)',
  PENDING: 'rgb(0 170 255)'
}

const SHORT_STATE: Record<StateKind, string> = {
  UP: _t('UP'),
  OK: _t('OK'),
  WARNING: _t('WARN'),
  DOWN: _t('DOWN'),
  CRITICAL: _t('CRIT'),
  UNREACHABLE: _t('UNREACH'),
  UNKNOWN: _t('UNKN'),
  PENDING: _t('PEND')
}

const stateKind = computed<StateKind>(() =>
  props.value.has_been_checked ? props.value.state : 'PENDING'
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
      :fill="STATE_COLOR[stateKind]"
      aria-hidden="true"
    />
    <ContextualLinkTrigger
      :links="value.links"
      :link-properties="value.link_properties"
      :filters="filters"
      :interactive="interactive"
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
        {{ SHORT_STATE[stateKind] }}
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
