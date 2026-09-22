<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The arrowhead on a directed geo line's end.

Its own marker rather than part of the line, because Leaflet draws the line as a
plain polyline: the head sits on the endpoint's coordinate and is turned to the
bearing the line arrives at.
-->
<script setup lang="ts">
defineProps<{
  /** The line's colour, resolved — the head is drawn outside CSS. */
  color: string
  /** Bearing the line arrives at, in degrees clockwise from north. */
  degrees: number
}>()
</script>

<template>
  <svg
    class="maps-world-map-line-arrow"
    viewBox="-6 -6 12 12"
    aria-hidden="true"
    :style="{ transform: `rotate(${degrees}deg)`, fill: color }"
  >
    <polygon points="0,-7 5,5 -5,5" />
  </svg>
</template>

<style scoped>
.maps-world-map-line-arrow {
  width: 12px;
  height: 12px;
  overflow: visible;
}
</style>
