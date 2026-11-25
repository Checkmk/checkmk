<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!-- The caption above a grid's frame. -->
<template>
  <span class="maps-map-grid-chip"><slot /></span>
</template>

<style scoped>
.maps-map-grid-chip {
  margin-bottom: var(--dimension-2);
  padding: var(--dimension-1) var(--dimension-3);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
  color: var(--font-color);
  font-size: var(--font-size-small);
  white-space: nowrap;
}
</style>
