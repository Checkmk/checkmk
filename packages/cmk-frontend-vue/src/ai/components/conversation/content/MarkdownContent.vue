<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'

import { markdown } from '@/ai/lib/markdown'
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
  parsedMarkdown.value = await markdown.parse(props.content)

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
    data-testid="ai-markdown-content"
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

/* stylelint-disable selector-pseudo-class-no-unknown */
.ai-markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: var(--dimension-4) 0;
  font-size: inherit;
}

.ai-markdown-content :deep(th),
.ai-markdown-content :deep(td) {
  padding: var(--dimension-4);
  text-align: left;
  vertical-align: top;
  border-bottom: var(--border-width-1) solid var(--default-border-color);
}

.ai-markdown-content :deep(thead th) {
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.ai-markdown-content :deep(tbody tr:last-child td) {
  border-bottom: none;
}

.ai-markdown-content :deep(h1),
.ai-markdown-content :deep(h2),
.ai-markdown-content :deep(h3),
.ai-markdown-content :deep(h4) {
  margin: var(--dimension-7) 0 var(--dimension-4);
  padding-left: 0;
  text-indent: 0;
  font-size: var(--font-size-xlarge);
  color: var(--font-color-dimmed);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.ai-markdown-content :deep(h2),
.ai-markdown-content :deep(h3),
.ai-markdown-content :deep(h4) {
  font-size: var(--font-size-large);
}

.ai-markdown-content :deep(.ai-markdown-content__badge) {
  display: inline-block;
  padding: 0 var(--dimension-3);
  border-radius: var(--dimension-2);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.05em;
  line-height: 1.6;
  white-space: nowrap;
  color: var(--black);
}

.ai-markdown-content :deep(.ai-markdown-content__badge--ok) {
  background-color: var(--color-corporate-green-50);
}

.ai-markdown-content :deep(.ai-markdown-content__badge--warn) {
  background-color: var(--color-yellow-50);
}

.ai-markdown-content :deep(.ai-markdown-content__badge--crit) {
  background-color: var(--color-light-red-50);
  color: var(--white);
}

.ai-markdown-content :deep(.ai-markdown-content__badge--unknown) {
  background-color: var(--color-orange-50);
}
/* stylelint-enable selector-pseudo-class-no-unknown */
</style>
