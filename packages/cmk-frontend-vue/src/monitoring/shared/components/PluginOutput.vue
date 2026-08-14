<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { type OutputSegment, splitStateMarkers } from '@/monitoring/shared/stateMarkers'

import ServiceStateDisplay from './ServiceStateDisplay.vue'
import { softBreak } from './cell/base/useSoftBreak'

const props = defineProps<{
  output: string
  /** Break opportunities for a cell that has to wrap; omit to keep the text as written. */
  hardBreakEvery?: number | undefined
}>()

const segments = computed<OutputSegment[]>(() =>
  splitStateMarkers(props.output).map((segment) =>
    segment.type === 'text' && props.hardBreakEvery !== undefined
      ? { type: 'text', text: softBreak(segment.text, props.hardBreakEvery) }
      : segment
  )
)
</script>

<template>
  <span class="monitoring-plugin-output">
    <template v-for="(segment, index) in segments" :key="index">
      <ServiceStateDisplay
        v-if="segment.type === 'marker'"
        class="monitoring-plugin-output__marker"
        inline
        :state="segment.state"
      />
      <template v-else>{{ segment.text }}</template>
    </template>
  </span>
</template>

<style scoped>
.monitoring-plugin-output__marker {
  margin: 0 var(--dimension-2);
  vertical-align: middle;
}
</style>
