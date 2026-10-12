<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The attention pulse around an object in a problem state: a circle that grows out
of where the utilisation ring sits and fades, on repeat.

It does not depend on the ring, so a host — which carries no ring — pulses the
same way as a service.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { ringGeometry } from '@/maps/map/elements/composables/arcRing'

/** How far past the ring the pulse grows before it has faded out. */
const REACH = 8

const props = defineProps<{
  iconSize: number
  /** The state colour, as a CSS colour value. */
  color: string
}>()

const geometry = computed(() => {
  const { innerRadius, outerRadius } = ringGeometry(props.iconSize)
  const reach = outerRadius + REACH
  return { size: reach * 2, from: innerRadius / reach }
})
</script>

<template>
  <span
    class="maps-map-element-pulse"
    aria-hidden="true"
    :style="{
      width: `${geometry.size}px`,
      height: `${geometry.size}px`,
      borderColor: color,
      '--maps-map-element-pulse-from': geometry.from
    }"
  />
</template>

<style scoped>
/* An HTML box rather than an SVG circle, so the browser can scale and fade it
   on the compositor instead of repainting every pulsing object each frame. */
.maps-map-element-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  box-sizing: border-box;
  border: 1.5px solid;
  border-radius: 50%;
  pointer-events: none;
  animation: maps-map-element-pulse 0.9s cubic-bezier(0.33, 1, 0.68, 1) infinite;
}

@keyframes maps-map-element-pulse {
  from {
    opacity: 0.7;
    transform: translate(-50%, -50%) scale(var(--maps-map-element-pulse-from));
  }

  to {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-map-element-pulse {
    display: none;
  }
}
</style>
