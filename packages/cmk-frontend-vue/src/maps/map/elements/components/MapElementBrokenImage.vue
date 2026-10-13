<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Stand-in for an image object whose file is missing.

Imports from NagVis routinely reference shapes the site does not have. A
broken-image glyph in the object's own footprint makes the gap obvious at a
glance, without pulling the operator into the file name.
-->
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  size: number
  /** The referenced file, shown on hover. */
  source: string
}>()

const boxStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))
const glyphSize = computed(() => `${Math.min(Math.round(props.size * 0.55), 32)}px`)
</script>

<template>
  <div class="maps-map-element-broken-image" :style="boxStyle" :title="`Asset missing: ${source}`">
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      :style="{ width: glyphSize, height: glyphSize }"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 17l6-6 4 4 4-4 4 4" />
      <line x1="3" y1="3" x2="21" y2="21" />
    </svg>
  </div>
</template>

<style scoped>
.maps-map-element-broken-image {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--maps-map-view-missing-ink);
  background: var(--maps-map-view-missing-bg);
  border: 1px dashed var(--maps-map-view-missing-ink);
  border-radius: var(--border-radius-half);
  pointer-events: none;
}
</style>
