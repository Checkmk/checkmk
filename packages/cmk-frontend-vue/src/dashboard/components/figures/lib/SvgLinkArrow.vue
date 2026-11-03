<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The menu arrow of an SVG link with several destinations. It follows the text right before it,
which only the browser can measure, so it needs to know when that text may have moved.
-->
<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef, watchPostEffect } from 'vue'

const TRIANGLE_UP_ASSET_HEIGHT_PER_WIDTH = 7 / 11

const props = defineProps<{
  /** What the text's content and position depend on: the arrow measures it anew on a change. */
  layout: string
  size: number
}>()

const arrow = useTemplateRef<SVGPolygonElement>('arrow')
const start = ref({ x: 0, y: 0 })

function measure(): void {
  const text = arrow.value?.previousElementSibling as SVGGraphicsElement | null | undefined
  if (typeof text?.getBBox !== 'function') {
    return
  }
  const box = text.getBBox()
  start.value = { x: box.x + box.width + props.size / 2, y: box.y + box.height / 2 }
}

watchPostEffect(() => {
  void props.layout
  measure()
})

// A web font that loads after the first measurement widens the text. jsdom loads no fonts.
onMounted(() => {
  if ('fonts' in document) {
    void document.fonts.ready.then(measure)
  }
})

const points = computed(() => {
  const { x, y } = start.value
  const rise = (props.size * TRIANGLE_UP_ASSET_HEIGHT_PER_WIDTH) / 2
  return `${x},${y - rise} ${x + props.size},${y - rise} ${x + props.size / 2},${y + rise}`
})
</script>

<template>
  <polygon
    ref="arrow"
    class="db-contextual-link-anchor__arrow db-svg-link-arrow"
    :points="points"
    aria-hidden="true"
  />
</template>

<style scoped>
.db-svg-link-arrow {
  fill: var(--font-color);
}
</style>
