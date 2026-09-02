<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The ring drawn around an object's icon, showing how utilised it is.

Its own overlay SVG, which D3 owns outright — that keeps the animated arc out of
Vue's hands, and pointer-events off it (as an attribute as well as a style, so no
browser's SVG inheritance can differ) keeps it from swallowing drags on the icon
underneath.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, useTemplateRef } from 'vue'

import { RING_PAD } from '@/maps/map/static/composables/arcRing'
import { useArcRing } from '@/maps/map/static/composables/useArcRing'
import type { UtilizationRing } from '@/maps/map/static/composables/useUtilizationRing'

const { _t } = usei18n()

const props = defineProps<{
  ring: UtilizationRing
  iconSize: number
}>()

const svg = useTemplateRef<SVGSVGElement>('svg')
const size = computed(() => props.iconSize + RING_PAD * 2)

useArcRing({
  svgRef: svg,
  iconSize: computed(() => props.iconSize),
  pct: props.ring.pct,
  colors: props.ring.colors,
  pulsing: props.ring.pulsing,
  enabled: props.ring.visible
})
</script>

<template>
  <svg
    ref="svg"
    :width="size"
    :height="size"
    pointer-events="none"
    class="maps-map-element-utilization-ring"
    :style="{ top: `-${RING_PAD}px`, left: `-${RING_PAD}px` }"
    :title="_t('Utilization ring (first metric)')"
  />
</template>

<style scoped>
.maps-map-element-utilization-ring {
  position: absolute;
  pointer-events: none;
}
</style>
