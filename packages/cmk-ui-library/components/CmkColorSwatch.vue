<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  /** Any CSS color, typically a graph series color from the data. */
  color: string
}>()
</script>

<template>
  <span class="cmk-color-swatch" :style="{ background: color }" aria-hidden="true" />
</template>

<style scoped>
/* The bar the graph legends draw next to a series. */
.cmk-color-swatch {
  display: inline-block;
  flex: 0 0 auto;
  width: 4px;
  height: 16px;
  border-radius: var(--border-radius-half);
}
</style>
