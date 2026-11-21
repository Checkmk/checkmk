<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A text button that floats over a map, such as "100% ↺". It only looks the part;
where it sits is up to whoever places it.
-->
<template>
  <button type="button" class="maps-map-overlay-button">
    <slot />
  </button>
</template>

<style scoped>
.maps-map-overlay-button {
  z-index: 6;
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
</style>
