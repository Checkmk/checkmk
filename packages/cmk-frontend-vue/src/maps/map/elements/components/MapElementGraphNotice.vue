<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a graph object shows in place of a graph: waiting for the first samples,
or nothing to show at all.

It keeps the object's footprint, so a map in edit mode still lays out the way it
will once data arrives, and says why rather than just staying blank.
-->
<script setup lang="ts">
defineProps<{
  message: string
  /** A dashed outline reads as "not filled in yet" rather than as a frame. */
  dashed?: boolean
}>()
</script>

<template>
  <div
    class="maps-map-element-graph-notice"
    :class="dashed ? 'maps-map-element-graph-notice--dashed' : ''"
  >
    <svg
      class="maps-map-element-graph-notice__glyph"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="1.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
    <span class="maps-map-element-graph-notice__text">{{ message }}</span>
  </div>
</template>

<style scoped>
.maps-map-element-graph-notice {
  display: flex;
  box-sizing: border-box;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  color: var(--font-color-dimmed);
  border: 1px solid var(--default-border-color);
  border-radius: var(--dimension-4);
}

.maps-map-element-graph-notice--dashed {
  border: 2px dashed var(--default-border-color);
}

.maps-map-element-graph-notice__glyph {
  width: var(--dimension-8);
  height: var(--dimension-8);
}

.maps-map-element-graph-notice__text {
  padding: 0 var(--dimension-5);
  font-size: var(--font-size-normal);
  line-height: 16px;
  text-align: center;
}
</style>
