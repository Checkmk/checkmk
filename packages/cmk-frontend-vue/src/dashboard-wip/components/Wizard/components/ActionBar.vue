<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

interface ActionBarProps {
  alignItems?: 'left' | 'center' | 'right'
}

const { alignItems = 'left' } = defineProps<ActionBarProps>()

const flexAlignment = computed(() => {
  switch (alignItems) {
    case 'center':
      return 'center'
    case 'right':
      return 'flex-end'
    default:
      return 'flex-start'
  }
})
</script>

<template>
  <!-- <div class="db-action-bar" :style="`justifyContent: ${flexAlignmentMap[props.alignItems]}`"> -->
  <div class="db-action-bar">
    <slot />
  </div>
</template>

<style scoped>
.db-action-bar {
  display: flex;
  gap: var(--spacing-double);
  justify-content: v-bind(flexAlignment);
}
</style>
