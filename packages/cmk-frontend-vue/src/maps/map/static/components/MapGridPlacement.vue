<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Where a grid being placed will go: the frame of its first row, as wide as the
objects a row holds, under the pointer. How many rows follow depends on what
its filter matches, which is only known once it is placed, so the frame fades
out below.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import { CANVAS_SCALE } from '@/maps/map/static/composables/useCanvasViewport'
import { gridLayout } from '@/maps/map/static/gridMembers'
import type { MapElement } from '@/maps/types/api'

import MapGridChip from './MapGridChip.vue'

const { _tn } = usei18n()

const props = defineProps<{
  grid: MapElement
  iconSize: number
  boxStyle: Record<string, string | number | undefined>
}>()

const FRAME_PADDING = 'var(--dimension-4)'

const canvasScale = inject(
  CANVAS_SCALE,
  computed(() => ({ sx: 1, sy: 1 }))
)

const layout = computed(() => gridLayout(props.grid))

const frameStyle = computed(() => ({
  width: `calc(${(layout.value.perRow - 1) * layout.value.offsetX * canvasScale.value.sx + props.iconSize}px + 2 * ${FRAME_PADDING})`,
  height: `calc(${props.iconSize}px + 2 * ${FRAME_PADDING})`
}))

const caption = computed(() =>
  _tn('%{n} per row', '%{n} per row', layout.value.perRow, { n: layout.value.perRow })
)
</script>

<template>
  <div
    class="maps-map-grid-placement"
    aria-hidden="true"
    :style="{ ...boxStyle, width: `${iconSize}px`, height: `${iconSize}px` }"
  >
    <div class="maps-map-grid-placement__extent">
      <MapGridChip>{{ caption }}</MapGridChip>
      <div class="maps-map-grid-placement__frame" :style="frameStyle" />
    </div>
  </div>
</template>

<style scoped>
.maps-map-grid-placement {
  position: absolute;
  pointer-events: none;
}

.maps-map-grid-placement__extent {
  position: absolute;
  bottom: calc(-1 * var(--dimension-4));
  left: calc(-1 * var(--dimension-4));
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.maps-map-grid-placement__frame {
  box-sizing: border-box;
  border: 1px dashed var(--interactive-accent);
  border-bottom: none;
  border-radius: var(--border-radius) var(--border-radius) 0 0;
  background: linear-gradient(
    color-mix(in srgb, var(--interactive-accent) 12%, transparent),
    transparent
  );
  mask-image: linear-gradient(black 60%, transparent);
}
</style>
