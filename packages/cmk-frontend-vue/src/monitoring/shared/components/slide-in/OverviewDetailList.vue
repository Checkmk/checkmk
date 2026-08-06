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
  display: grid;
  grid-template-columns: minmax(120px, max-content) 1fr;
  gap: var(--dimension-4) var(--spacing);
  margin: 0;
}

.monitoring-overview-detail-list--start {
  align-items: start;
}

.monitoring-overview-detail-list :slotted(dt) {
  color: var(--font-color);
}

.monitoring-overview-detail-list :slotted(dd) {
  margin: 0;
}
</style>
