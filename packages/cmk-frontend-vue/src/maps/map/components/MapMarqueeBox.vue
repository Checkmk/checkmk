<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The rubber band a map draws while the operator pulls a selection.

Every map type that supports the gesture draws the same band, so it looks the
same on all of them; where it sits in the canvas's own stacking order is the
canvas's business, hence ``layer``.
-->
<script setup lang="ts">
import type { MarqueeRect } from '@/maps/map/composables/useMarquee'

defineProps<{
  rect: MarqueeRect
  /** Stacking order inside the canvas that draws it. */
  layer?: number
}>()
</script>

<template>
  <div
    class="maps-map-marquee-box"
    :style="{
      left: `${rect.left}px`,
      top: `${rect.top}px`,
      width: `${rect.width}px`,
      height: `${rect.height}px`,
      zIndex: layer
    }"
  />
</template>

<style scoped>
.maps-map-marquee-box {
  position: absolute;
  background: color-mix(in srgb, var(--color-corporate-green-50) 12%, transparent);
  border: 1px solid var(--color-corporate-green-50);
  pointer-events: none;
}
</style>
