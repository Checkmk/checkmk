<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

const { text, suffixCount = 6 } = defineProps<{ text: string; suffixCount?: number }>()

const startText = computed(() => text.slice(0, -suffixCount))
const endText = computed(() => text.slice(-suffixCount))
</script>

<template>
  <span class="cmk-truncate-text" :aria-label="text" :title="text"
    ><span class="cmk-truncate-text__start">{{ startText }}</span
    ><span class="cmk-truncate-text__end">{{ endText }}</span></span
  >
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
  white-space: pre;
}

.cmk-truncate-text__end {
  flex-shrink: 0;
  white-space: pre;
}
</style>
