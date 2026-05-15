<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// Cells with `breakpoint` are hidden on viewports narrower than the canonical
// breakpoint of the same name (see `@/assets/breakpoints`).
type CellBreakpoint = 's' | 'm' | 'l' | 'xl'

defineProps<{
  breakpoint?: CellBreakpoint
}>()
</script>

<template>
  <td :class="breakpoint ? `monitoring-table-cell--breakpoint-${breakpoint}` : null">
    <slot />
  </td>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.monitoring-table-cell--breakpoint-s,
.monitoring-table-cell--breakpoint-m,
.monitoring-table-cell--breakpoint-l,
.monitoring-table-cell--breakpoint-xl {
  display: none;
}

@include bp.viewport-up(s) {
  .monitoring-table-cell--breakpoint-s {
    display: revert;
  }
}

@include bp.viewport-up(m) {
  .monitoring-table-cell--breakpoint-m {
    display: revert;
  }
}

@include bp.viewport-up(l) {
  .monitoring-table-cell--breakpoint-l {
    display: revert;
  }
}

@include bp.viewport-up(xl) {
  .monitoring-table-cell--breakpoint-xl {
    display: revert;
  }
}
</style>
