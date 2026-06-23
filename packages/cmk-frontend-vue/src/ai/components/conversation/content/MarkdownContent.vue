<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'

import { parseMarkdown } from '@/ai/lib/markdown'
import type {
  MarkdownConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'
import { typewriter } from '@/ai/lib/utils'

const props = defineProps<MarkdownConversationElementContent>()
const parsedMarkdown = ref<string>()
const typedText = ref<string>('')
const emit = defineEmits<TBaseConversationElementEmits>()

async function renderMarkdown(): Promise<void> {
  const renderedContent = props.content
  const parsed = await parseMarkdown(renderedContent)
  if (renderedContent !== props.content) {
    return
  }
  parsedMarkdown.value = parsed

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
  padding-bottom: var(--dimension-10);
}

.ai-markdown-content--thinking {
  font-style: italic;
  font-weight: 400;
  color: var(--font-color-dimmed);
  border: 1px solid var(--default-form-element-bg-color);
  border-radius: var(--dimension-2);
  padding: 0 var(--dimension-6) var(--dimension-2) var(--dimension-6);
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ai-markdown-content :deep(p) {
  line-height: var(--dimension-8);
}

.ai-markdown-content :deep(code) {
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.ai-markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: var(--dimension-4) 0;
  font-size: inherit;
}

.ai-markdown-content :deep(th) {
  height: var(--dimension-8);
  padding: 0 var(--dimension-4);
  letter-spacing: 0.08em;
  color: var(--font-color-dimmed);
  text-align: left;
  vertical-align: middle;
  background-color: var(--odd-tr-bg-color);
}

.ai-markdown-content :deep(td) {
  padding: var(--dimension-4);
  letter-spacing: 0.04em;
  text-align: left;
  vertical-align: top;
}

/* The header already uses the odd-row token, so start tbody striping with the even-row token. */
.ai-markdown-content :deep(tbody tr:nth-child(odd)) {
  background-color: var(--even-tr-bg-color);
}

.ai-markdown-content :deep(tbody tr:nth-child(even)) {
  background-color: var(--odd-tr-bg-color);
}

/* Markdown can begin with a heading; drop its top margin to avoid extra space at the top. */
.ai-markdown-content :deep(h1:first-child) {
  margin-top: 0;
}

.ai-markdown-content :deep(h1),
.ai-markdown-content :deep(h2),
.ai-markdown-content :deep(h3),
.ai-markdown-content :deep(h4) {
  margin: var(--dimension-10) 0 var(--dimension-5);
  padding-left: 0;
  text-indent: 0;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.ai-markdown-content :deep(.ai-markdown-content__service-context) {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.ai-markdown-content :deep(.ai-markdown-content__service-context > li) {
  border: 2px solid var(--default-border-color);
  border-radius: var(--dimension-3);
  padding: var(--dimension-5) var(--dimension-6);
  line-height: var(--dimension-7);
}

.ai-markdown-content :deep(.ai-markdown-content__recommended-actions) {
  list-style: none;
  padding: 0;
  margin: 0;
  counter-reset: ai-recommended-action;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.ai-markdown-content :deep(.ai-markdown-content__recommended-actions > li) {
  counter-increment: ai-recommended-action;
  position: relative;
  background-color: var(--even-tr-bg-color);
  border-radius: var(--dimension-3);
  padding: var(--dimension-5) var(--dimension-6);
  padding-left: calc(var(--dimension-6) + var(--dimension-8) + var(--dimension-6));
  line-height: var(--dimension-7);
}

.ai-markdown-content :deep(.ai-markdown-content__recommended-actions > li::before) {
  content: counter(ai-recommended-action);
  position: absolute;
  left: var(--dimension-6);
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-8);
  height: var(--dimension-8);
  background-color: var(--ai-action-badge-bg);
  border: 1px solid var(--border-color-purple);
  border-radius: 50%;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
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
