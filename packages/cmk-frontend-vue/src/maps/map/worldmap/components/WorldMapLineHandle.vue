<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The grip on one end of a geo line, shown while the map is being edited.

It takes the line's own colour so the operator can tell which line they are
about to grab, and switches to the accent colour once the end is bound to an
object — that is the one thing about an end that is not visible from the line.
-->
<script setup lang="ts">
defineProps<{
  /** The line's colour, resolved — the grip is drawn outside CSS. */
  color: string
  /** Whether this end follows an object rather than a fixed coordinate. */
  bound?: boolean
}>()
</script>

<template>
  <div
    class="maps-world-map-line-handle"
    :class="{ 'maps-world-map-line-handle--bound': bound }"
    :style="bound ? undefined : { background: color }"
  />
</template>

<style scoped>
.maps-world-map-line-handle {
  width: 10px;
  height: 10px;
  border: 2px solid var(--white);
  border-radius: 9999px;
  box-shadow: 0 1px 3px rgb(0 0 0 / 50%);
  cursor: move;
}

.maps-world-map-line-handle--bound {
  background: var(--color-corporate-green-50);
}
</style>
