<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

const { text, suffixCount = 6 } = defineProps<{ text: string; suffixCount?: number }>()

// Replaces trailing (start) and leading (end) spaces with non-breaking spaces
// to prevent them from being collapsed when truncated with ellipsis
const startText = computed(() => {
  const start = text.slice(0, -suffixCount)
  return start.replace(/\s+$/, (match) => '\u00A0'.repeat(match.length))
})
const endText = computed(() => {
  const end = text.slice(-suffixCount)
  return end.replace(/^\s+/, (match) => '\u00A0'.repeat(match.length))
})
</script>

<template>
  <span class="cmk-truncate-text" :aria-label="text" :title="text">
    <span class="cmk-truncate-text__start">{{ startText }}</span>
    <span class="cmk-truncate-text__end">{{ endText }}</span>
  </span>
</template>

<style scoped>
.cmk-truncate-text {
  display: flex;
  align-items: baseline;
  white-space: nowrap;
  overflow: hidden;
}

.cmk-truncate-text__start {
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
}

.cmk-truncate-text__end {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
