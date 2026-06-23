<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts"></script>

<template>
  <div class="monitoring-state-icon">
    <slot />
  </div>
</template>

<style scoped>
.monitoring-state-icon {
  background-color: var(--ux-theme-5);
  border-radius: var(--border-radius);
  height: var(--dimension-7);
  width: var(--dimension-7);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
