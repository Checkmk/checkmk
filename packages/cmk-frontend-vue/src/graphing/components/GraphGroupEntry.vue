<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { computed, ref, watch } from 'vue'

import type { GraphLoad, ResolvedGraph } from '../composables/useGraphData'
import type { GraphNoticeDescriptor } from '../composables/useGraphNotice'
import { useNearView } from '../composables/useNearView'
import GraphSkeleton from './GraphSkeleton.vue'

const props = defineProps<{
  load: GraphLoad
  notice: GraphNoticeDescriptor | null
  figureWidth: number
  figureHeight: number
  showLegend: boolean
  showBrush: boolean
}>()

const emit = defineEmits<{
  'near-view': [isNear: boolean]
  retry: []
}>()

defineSlots<{
  panel(props: { graph: ResolvedGraph }): unknown
}>()

const root = ref<HTMLElement | null>(null)

const isNearView = useNearView(root)
watch(isNearView, (isNear) => emit('near-view', isNear), { immediate: true })

// A refetch is skeletonised too: the curves still on screen are the previous range's, so leaving
// them up reads as nothing having happened. Only that case is worth delaying: a graph that has
// never loaded shows its skeleton at once. A failure is exempt either way, its notice occupies
// the area.
const delayHasElapsed = useDelayedFlag(
  () => props.load.isLoading && props.load.error === null,
  LOADING_AFFORDANCE_DELAY_MS
)

const isSkeleton = computed(
  () =>
    props.load.error === null &&
    (props.load.graph === null || (props.load.isLoading && delayHasElapsed.value))
)

function contentHeight(element: HTMLElement): number {
  const style = getComputedStyle(element)
  const padding = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0)
  return element.getBoundingClientRect().height - padding
}

// Read as a refetch's skeleton goes up but before it renders, so the panel it replaces is still on
// screen and the skeleton can hold that panel's footprint.
const refetchHeight = ref<number | undefined>(undefined)
watch(isSkeleton, (showsSkeleton) => {
  if (showsSkeleton && props.load.graph !== null && root.value !== null) {
    refetchHeight.value = contentHeight(root.value)
  }
})
</script>

<template>
  <div
    ref="root"
    :class="
      isSkeleton || load.graph
        ? 'graphing-graph-group__panel'
        : 'graphing-graph-group__notice--standalone'
    "
  >
    <GraphSkeleton
      v-if="isSkeleton"
      :figure-width="figureWidth"
      :figure-height="figureHeight"
      :show-legend="showLegend"
      :show-brush="showBrush"
      :height="load.graph === null ? undefined : refetchHeight"
    />
    <slot v-else-if="load.graph" name="panel" :graph="load.graph" />
    <!-- A first load that failed has no panel to sit over, so its notice stands on its own. -->
    <CmkSurfaceNotice v-else-if="notice" v-bind="notice" silent @retry="emit('retry')" />
  </div>
</template>

<style scoped lang="scss">
// Unset, the panels sit bare in the group; a page that wants each graph on its own box sets these.
.graphing-graph-group__panel {
  position: relative;
  padding: var(--graphing-graph-group-panel-padding, 0);
  background-color: var(--graphing-graph-group-panel-background, transparent);
  border-radius: var(--graphing-graph-group-panel-border-radius, 0);
}

.graphing-graph-group__notice--standalone {
  align-self: center;
}
</style>
