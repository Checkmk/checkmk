<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The alignment grid shown while editing a static map.

Its ``viewBox`` is the map's own coordinate space, so the drawn intervals are
exactly the ones a drag snaps to even after the canvas has been stretched to fit
its pane.
-->
<script setup lang="ts">
import useId from 'cmk-ui-library/lib/useId'

defineProps<{
  /** Snap interval, in map units. */
  size: number
  width: number
  height: number
}>()

const patternId = `maps-map-canvas-grid-${useId()}`
</script>

<template>
  <svg
    class="maps-map-canvas-grid"
    :viewBox="`0 0 ${width} ${height}`"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <defs>
      <pattern :id="patternId" :width="size" :height="size" patternUnits="userSpaceOnUse">
        <path
          class="maps-map-canvas-grid__line"
          :d="`M ${size} 0 L 0 0 0 ${size}`"
          fill="none"
          stroke-width="1"
        />
      </pattern>
    </defs>
    <rect width="100%" height="100%" :fill="`url(#${patternId})`" />
  </svg>
</template>

<style scoped>
.maps-map-canvas-grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.maps-map-canvas-grid__line {
  stroke: var(--maps-map-view-grid);
}
</style>
