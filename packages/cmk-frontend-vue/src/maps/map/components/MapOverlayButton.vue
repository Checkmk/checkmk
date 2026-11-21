<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A text button that floats over a map, such as "100% ↺". It only looks the part;
where it sits is up to whoever places it.
-->
<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Whether what it opens is open; left out by a button that opens nothing. */
    expanded?: boolean | undefined
  }>(),
  { expanded: undefined }
)
</script>

<template>
  <button type="button" class="maps-map-overlay-button" :aria-expanded="expanded">
    <slot />
    <svg
      v-if="expanded !== undefined"
      class="maps-map-overlay-button__caret"
      :class="{ 'maps-map-overlay-button__caret--open': expanded }"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  </button>
</template>

<style scoped>
.maps-map-overlay-button {
  z-index: 6;
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);

  /* Checkmk's global button margin would push it off where it is placed. */
  margin: 0;
  padding: var(--dimension-4) var(--dimension-5);
  border-radius: var(--border-radius);

  /* May be teleported out of the map view, so it cannot inherit the map's
     overlay surface and names the tooltip surface that one stands for. */
  background: var(--default-tooltip-background-color);
  border: 1px solid var(--default-border-color);
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
}

.maps-map-overlay-button:hover {
  border-color: var(--interactive-accent);
}

.maps-map-overlay-button__caret {
  width: 10px;
  height: 10px;
  transition: transform 0.15s;
}

.maps-map-overlay-button__caret--open {
  transform: rotate(180deg);
}
</style>
