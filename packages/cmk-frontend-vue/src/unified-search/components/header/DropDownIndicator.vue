<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  active: boolean
}>()
</script>

<template>
  <span class="cmk-dropdown-indicator" :class="{ active }"></span>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-dropdown-indicator {
  width: 16px;

  &::after {
    border-color: var(--help-text-font-color);
    border-style: solid;
    border-width: 2px 2px 0 0;
    content: '';
    display: inline-block;
    width: 6px;
    height: 6px;
    position: relative;
    transform: rotate(135deg);
    top: -1px;
    transition:
      transform 0.3s ease-in-out,
      top 0.3s ease-in-out;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.active {
  &::after {
    transform: rotate(-45deg);
    top: 3px;
    transition:
      transform 0.3s ease-out,
      top 0.3s ease-out;
  }
}
</style>
