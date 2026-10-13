<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The chrome every floating surface of the presentation editor wears -- the
insert palette, the align bar, the history bar, the layers panel, the connect
bar and its popover.

It only paints the surface; where each of them sits, and how it lays its
contents out, stays with the panel itself (its own class lands on this root
through Vue's attribute fallthrough).
-->
<script setup lang="ts">
withDefaults(
  defineProps<{
    /** For a panel that overlaps the others and needs to read as being on top. */
    raised?: boolean
  }>(),
  { raised: false }
)
</script>

<template>
  <div class="maps-presentation-panel" :class="{ 'maps-presentation-panel--raised': raised }">
    <slot />
  </div>
</template>

<style scoped>
.maps-presentation-panel {
  border-radius: 10px;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  box-shadow: 0 8px 24px rgb(0 0 0 / 30%);
}

.maps-presentation-panel--raised {
  box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
}
</style>
