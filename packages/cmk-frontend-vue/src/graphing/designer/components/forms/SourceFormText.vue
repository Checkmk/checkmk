<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  variant: 'name' | 'description'
}>()
</script>

<template>
  <span :class="`graphing-source-form-text--${variant}`">
    <slot />
  </span>
</template>

<style scoped>
.graphing-source-form-text--name {
  font-weight: var(--font-weight-bold);
}

.graphing-source-form-text--description {
  font-style: italic;
}
</style>
