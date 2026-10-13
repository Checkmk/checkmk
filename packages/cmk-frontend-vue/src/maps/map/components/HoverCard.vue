<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The frame every hover card on a map stands in. Where it opens is the caller's.
-->
<script setup lang="ts">
const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
}>()
</script>

<template>
  <div class="maps-hover-card" @mouseenter="emit('card-enter')" @mouseleave="emit('card-leave')">
    <slot />
  </div>
</template>

<style scoped>
.maps-hover-card {
  min-width: 208px;
  max-width: 288px;
  padding: 14px;
  background: var(--maps-map-view-glass);
  backdrop-filter: blur(12px);
  border-radius: var(--dimension-5);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);

  /* Hoverable for its links; leaving it re-schedules the close. */
  pointer-events: auto;
}
</style>
