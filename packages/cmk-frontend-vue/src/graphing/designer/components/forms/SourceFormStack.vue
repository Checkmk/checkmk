<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  spacing: 'label' | 'field' | 'section'
}>()
</script>

<template>
  <div class="graphing-source-form-stack" :class="`graphing-source-form-stack--${spacing}`">
    <slot />
  </div>
</template>

<style scoped>
.graphing-source-form-stack {
  display: flex;
  flex-direction: column;
}

.graphing-source-form-stack--label {
  gap: var(--dimension-4);
}

.graphing-source-form-stack--field {
  gap: var(--dimension-6);
}

.graphing-source-form-stack--section {
  gap: var(--dimension-7);
}
</style>
