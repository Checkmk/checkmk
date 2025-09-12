<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
interface ActionBarProps {
  alignItems?: 'left' | 'center' | 'right'
}

const props = withDefaults(defineProps<ActionBarProps>(), {
  alignItems: 'left'
})

const flexAlignmentMap = {
  left: 'flex-start',
  center: 'center',
  right: 'flex-end'
}
</script>

<template>
  <div class="db-action-bar" :style="`justifyContent: ${flexAlignmentMap[props.alignItems]}`">
    <slot />
  </div>
</template>

<style scoped>
.db-action-bar {
  display: flex;
  gap: var(--spacing-double);
}
</style>
