<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import type {
  ListConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

defineProps<ListConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <ul v-if="listType === 'unordered'" class="ai-list-content">
    <li v-for="item in items" :key="item">{{ item }}</li>
  </ul>
  <ol v-else class="ai-list-content">
    <li v-for="item in items" :key="item">{{ item }}</li>
  </ol>
</template>

<style scoped>
.ai-list-content {
  padding: var(--dimension-4);
}
</style>
