<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
defineProps<{ num: number }>()
</script>

<template>
  <div class="cmk-zebra" :class="[{ odd: num % 2 > 0 }, { even: num % 2 === 0 }]"><slot /></div>
</template>

<style scoped>
.cmk-zebra {
  width: 100%;
  height: 100%;

  &.even {
    --default-bg-color: var(--ux-theme-3);
  }
  &.odd {
    --default-bg-color: var(--ux-theme-2);
  }
}
</style>
