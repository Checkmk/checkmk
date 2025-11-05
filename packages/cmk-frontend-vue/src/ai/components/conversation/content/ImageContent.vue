<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import type {
  ImageConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

defineProps<ImageConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <img class="ai-image-content" :src="src" :alt="altText || 'ai provide image'" />
</template>

<style scoped>
.ai-image-content {
  margin: var(--dimension-4);
  width: 400px;
}
</style>
