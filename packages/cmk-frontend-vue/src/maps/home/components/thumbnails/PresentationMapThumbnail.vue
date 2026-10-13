<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a presentation looks like, for the list: a slide with a heading and two
data widgets. An illustration — the slide's own elements are only rendered once
the presentation is opened.
-->
<script setup lang="ts">
import type { ThumbnailState } from '@/maps/home/components/thumbnails/palette'

interface Bar {
  x: number
  y: number
  height: number
  state: ThumbnailState
}

const BARS: readonly Bar[] = [
  { x: 118, y: 80, height: 18, state: 'ok' },
  { x: 129, y: 70, height: 28, state: 'warn' },
  { x: 140, y: 86, height: 12, state: 'ok' }
]
</script>

<template>
  <svg viewBox="0 0 256 128" class="maps-presentation-map-thumbnail">
    <rect width="256" height="128" class="maps-presentation-map-thumbnail__canvas" />
    <rect
      x="22"
      y="12"
      width="212"
      height="104"
      rx="6"
      class="maps-presentation-map-thumbnail__slide"
    />
    <rect
      x="34"
      y="22"
      width="86"
      height="7"
      rx="2"
      class="maps-presentation-map-thumbnail__title"
    />
    <rect
      x="34"
      y="33"
      width="54"
      height="4"
      rx="2"
      class="maps-presentation-map-thumbnail__subtitle"
    />

    <!-- Gauge widget -->
    <path d="M44 96 A22 22 0 0 1 88 96" class="maps-presentation-map-thumbnail__gauge-track" />
    <path d="M44 96 A22 22 0 0 1 79 78.4" class="maps-presentation-map-thumbnail__gauge-value" />
    <rect
      x="58"
      y="88"
      width="16"
      height="4"
      rx="2"
      class="maps-presentation-map-thumbnail__caption"
    />

    <!-- Bar-chart widget -->
    <rect
      x="110"
      y="56"
      width="46"
      height="48"
      rx="4"
      class="maps-presentation-map-thumbnail__panel"
    />
    <rect
      v-for="(bar, index) in BARS"
      :key="index"
      :x="bar.x"
      :y="bar.y"
      width="7"
      :height="bar.height"
      rx="1.5"
      class="maps-presentation-map-thumbnail__bar"
      :class="`maps-presentation-map-thumbnail__bar--${bar.state}`"
    />

    <!-- Single-value widget in a problem state -->
    <rect
      x="164"
      y="56"
      width="46"
      height="48"
      rx="4"
      class="maps-presentation-map-thumbnail__panel"
    />
    <circle cx="187" cy="74" r="9" class="maps-presentation-map-thumbnail__halo" />
    <circle cx="187" cy="74" r="5" class="maps-presentation-map-thumbnail__value" />
    <rect
      x="174"
      y="90"
      width="26"
      height="6"
      rx="2"
      class="maps-presentation-map-thumbnail__caption"
    />
  </svg>
</template>

<style scoped>
.maps-presentation-map-thumbnail__canvas {
  fill: var(--maps-map-thumbnail-canvas);
}

.maps-presentation-map-thumbnail__slide {
  fill: var(--maps-map-thumbnail-surface);
  stroke: color-mix(in srgb, var(--maps-map-thumbnail-label) 12%, transparent);
  stroke-width: 1;
}

.maps-presentation-map-thumbnail__title {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 78%, transparent);
}

.maps-presentation-map-thumbnail__subtitle {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 30%, transparent);
}

.maps-presentation-map-thumbnail__caption {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 40%, transparent);
}

.maps-presentation-map-thumbnail__gauge-track,
.maps-presentation-map-thumbnail__gauge-value {
  fill: none;
  stroke-width: 5;
  stroke-linecap: round;
}

.maps-presentation-map-thumbnail__gauge-track {
  stroke: var(--maps-map-thumbnail-edge);
}

.maps-presentation-map-thumbnail__gauge-value {
  stroke: var(--maps-map-thumbnail-ok);
}

.maps-presentation-map-thumbnail__panel {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 4%, transparent);
  stroke: color-mix(in srgb, var(--maps-map-thumbnail-label) 10%, transparent);
  stroke-width: 0.75;
}

.maps-presentation-map-thumbnail__bar--ok {
  fill: var(--maps-map-thumbnail-ok);
}

.maps-presentation-map-thumbnail__bar--warn {
  fill: var(--maps-map-thumbnail-warn);
}

.maps-presentation-map-thumbnail__bar--crit {
  fill: var(--maps-map-thumbnail-crit);
}

.maps-presentation-map-thumbnail__halo {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-crit) 22%, transparent);
}

.maps-presentation-map-thumbnail__value {
  fill: var(--maps-map-thumbnail-crit);
}
</style>
