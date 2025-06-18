<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <h1 class="cmk-heading1">
    <slot />
  </h1>
</template>

<style scoped>
.cmk-heading1 {
  font-size: var(--font-size-xxlarge);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  margin: 0;
}
</style>
