<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { marked } from 'marked'
import { ref, watch } from 'vue'

import type {
  MarkdownConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'
import { typewriter } from '@/ai/lib/utils'

const props = defineProps<MarkdownConversationElementContent>()
const parsedMarkdown = ref<string>()
const typedText = ref<string>('')
const emit = defineEmits<TBaseConversationElementEmits>()

async function renderMarkdown() {
  parsedMarkdown.value = await marked.parse(props.content, { breaks: true })

  if (props.noAnimation) {
    typedText.value = parsedMarkdown.value
    emit('done')
  } else {
    typedText.value = ''
    typewriter(typedText, parsedMarkdown.value, () => {
      emit('done')
    })
  }
}

watch(
  () => props.content,
  async () => {
    await renderMarkdown()
  },
  { immediate: true }
)
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="ai-markdown-content"
    :class="{ 'ai-markdown-content--thinking': props.title === 'thinking' }"
    v-html="typedText"
  ></div>
  <!-- eslint-enable vue/no-v-html -->
</template>

<style scoped>
.ai-markdown-content {
  padding-bottom: var(--dimension-4);
}

.ai-markdown-content--thinking {
  font-style: italic;
  font-weight: 400;
  color: var(--font-color-dimmed);
  border: 1px solid var(--default-form-element-bg-color);
  border-radius: var(--dimension-2);
  padding: 0 var(--dimension-6) var(--dimension-2) var(--dimension-6);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.ai-markdown-content :deep(code) {
  white-space: pre-wrap;
  overflow-wrap: break-word;
}
</style>
