<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <div class="graphing-graph-title">{{ title }}</div>
</template>

<style scoped>
.graphing-graph-title {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
}
</style>
