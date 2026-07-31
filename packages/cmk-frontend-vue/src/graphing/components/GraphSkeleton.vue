<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
A placeholder occupying one GraphPanel's footprint while its data is still being fetched.

Following the design's "skeleton by area", each of the panel's four areas becomes one block rather
than skeletonising the axis ticks, legend rows and controls inside them.

Decorative only; GraphGroup owns the announcement for assistive tech.
-->

<script setup lang="ts">
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'

// Matches GraphBrush's own HEIGHT, which it derives from its track and label geometry.
const brushHeight = '71px'

// An estimate of a typical legend, roughly a header plus five rows. The real one grows with the
// metric count, which is not known until the data arrives.
const legendHeight = '160px'

// GraphPanel's defaults, so an unsized skeleton covers the same box as the panel replacing it.
withDefaults(
  defineProps<{
    figureWidth?: number
    figureHeight?: number
  }>(),
  { figureWidth: 800, figureHeight: 300 }
)
</script>

<template>
  <div class="graphing-graph-skeleton" :style="{ width: `${figureWidth}px` }" aria-hidden="true">
    <div class="graphing-graph-skeleton__header">
      <CmkSkeleton type="text" width="120px" />
      <CmkSkeleton type="text" width="45%" />
    </div>
    <div class="graphing-graph-skeleton__plot" :style="{ height: `${figureHeight}px` }">
      <CmkSkeleton type="box" />
    </div>
    <div class="graphing-graph-skeleton__brush">
      <CmkSkeleton type="box" />
    </div>
    <div class="graphing-graph-skeleton__legend">
      <CmkSkeleton type="box" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-skeleton {
  pointer-events: none;
}

// The spacings below mirror GraphPanel's, so each block sits where its area will.
// Brush and legend span the whole figure, matching the real ones.
.graphing-graph-skeleton__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-double);
  margin-bottom: var(--spacing-double);
}

.graphing-graph-skeleton__brush {
  height: v-bind(brushHeight);
  margin-top: calc(var(--spacing) * 2);
}

.graphing-graph-skeleton__legend {
  height: v-bind(legendHeight);
  margin-top: calc(var(--spacing) * 2);
}
</style>
