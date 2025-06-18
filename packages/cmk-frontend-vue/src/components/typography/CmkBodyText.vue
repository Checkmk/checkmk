<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <p class="cmk-body-text">
    <slot />
  </p>
</template>

<style scoped>
.cmk-body-text {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  color: var(--font-color);
  margin: 0;
  line-height: normal;
  letter-spacing: 0.36px;
}
</style>
