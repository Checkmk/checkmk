<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { marked } from 'marked'
import { onMounted } from 'vue'

import type {
  MarkdownConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

const props = defineProps<MarkdownConversationElementContent>()

const emit = defineEmits<TBaseConversationElementEmits>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="ai-markdown-content" v-html="marked.parse(props.content)"></div>
</template>

<style scoped>
.ai-markdown-content {
  padding-bottom: var(--dimension-4);

  /* stylelint-disable-next-line selector-pseudo-class-no-unknown */
  :deep(code) {
    background: var(--code-background-color);
    border-radius: var(--border-radius);
  }
}
</style>
