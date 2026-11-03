<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkColorSwatch from 'cmk-ui-library/components/CmkColorSwatch.vue'
</script>

<template>
  <span class="ucl-cmk-color-swatch-code-example">
    <CmkColorSwatch color="#3cc2ff" />
    CPU utilization
  </span>
</template>

<style scoped>
.ucl-cmk-color-swatch-code-example {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
