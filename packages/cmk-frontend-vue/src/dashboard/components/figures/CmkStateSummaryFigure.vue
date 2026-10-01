<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { StateSummary, VisualContext } from '@/dashboard/types/widget'

import { valueFontSize } from './lib/valueFontSize'

const props = defineProps<{
  value: StateSummary
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const text = computed(() => `${props.value.in_state.count}/${props.value.total}`)

const fontSizePx = computed(
  () => `${valueFontSize((5 * props.width) / text.value.length, props.height)}px`
)
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-state-summary-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <ContextualLinkTrigger
      :links="value.links"
      :link-properties="value.in_state.link_properties"
      :filters="filters"
      :interactive="interactive"
    >
      <text
        class="db-cmk-state-summary-figure__text"
        :x="width / 2"
        :y="height / 2"
        text-anchor="middle"
        dominant-baseline="central"
      >
        {{ text }}
      </text>
    </ContextualLinkTrigger>
  </svg>
</template>

<style scoped>
.db-cmk-state-summary-figure {
  display: block;
}

.db-cmk-state-summary-figure__text {
  fill: var(--font-color);
  font-size: v-bind(fontSizePx);
  font-weight: bold;
}
</style>
