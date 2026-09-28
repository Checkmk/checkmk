<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// Rows stretch by default; `start` pins them to the top, for values as tall as a chip list.
defineProps<{ align?: 'start' }>()
</script>

<template>
  <dl
    class="monitoring-overview-detail-list"
    :class="align ? `monitoring-overview-detail-list--${align}` : undefined"
  >
    <slot />
  </dl>
</template>

<style scoped>
.monitoring-overview-detail-list {
  --monitoring-overview-detail-list-label-width: 140px;

  display: grid;
  grid-template-columns: var(--monitoring-overview-detail-list-label-width) minmax(0, 1fr);
  gap: var(--dimension-4) var(--spacing);
  margin: 0;
}

.monitoring-overview-detail-list--start {
  align-items: start;
}

.monitoring-overview-detail-list :slotted(dt) {
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
  hyphens: auto;
  overflow-wrap: break-word;
}

.monitoring-overview-detail-list :slotted(dd) {
  margin: 0;
  font-weight: var(--font-weight-default);
}
</style>
