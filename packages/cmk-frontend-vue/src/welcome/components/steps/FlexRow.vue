<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts"></script>

<template>
  <div class="flex-row">
    <slot />
  </div>
</template>

<style scoped>
.flex-row {
  margin-top: var(--spacing-half);
  display: flex;
  flex-direction: row;
  gap: var(--spacing);
}
</style>
