<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'
import type {
  AlertConversationElementContent,
  CodeBlockConversationElementContent,
  DialogConversationElementContent,
  IAiConversationElement,
  ImageConversationElementContent,
  ListConversationElementContent,
  MarkdownConversationElementContent,
  TAiConversationElementContent
} from '@/ai/lib/service/ai-template'
import { AiRole } from '@/ai/lib/utils'

import AlertContent from './content/AlertContent.vue'
import CodeContent from './content/CodeContent.vue'
import DialogContent from './content/DialogContent.vue'
import ImageContent from './content/ImageContent.vue'
import ListContent from './content/ListContent.vue'
import MarkdownContent from './content/MarkdownContent.vue'

const { _t } = usei18n()
const props = defineProps<IAiConversationElement & { elementIndex?: number }>()
const aiTemplate = getInjectedAiTemplate()

function filterThinkingForReopen(
  items: TAiConversationElementContent[]
): TAiConversationElementContent[] {
  const hasAnswer = items.some((c) => c.title === 'answer' || c.content_type === 'alert')
  if (hasAnswer) {
    return items.filter((c) => c.title !== 'thinking')
  }
  let lastThinking: TAiConversationElementContent | undefined
  for (let i = items.length - 1; i >= 0; i--) {
    if (items[i]?.title === 'thinking') {
      lastThinking = items[i]
      break
    }
  }
  const nonThinking = items.filter((c) => c.title !== 'thinking')
  return lastThinking ? [...nonThinking, lastThinking] : nonThinking
}

function initContentData(): TAiConversationElementContent[] | null {
  const items = Array.isArray(props.content) ? props.content : []
  if (props.streaming) {
    return items.length > 0 ? filterThinkingForReopen(items) : null
  }
  return filterThinkingForReopen(items)
}

const currentState = ref<string>(
  props.content?.length > 0 ? props.content[props.content.length - 1]?.title || '' : ''
)

const contentData = ref<TAiConversationElementContent[] | null>(initContentData())

// Separate display list for non-streaming animation; streaming uses contentData directly.
const contentsToDisplay = ref<TAiConversationElementContent[]>([])
const displayItems = computed(() => (props.streaming ? contentData.value : contentsToDisplay.value))
const hasDisplayableContent = computed(
  () => displayItems.value?.some((cnt) => cnt.content_type !== 'text') ?? false
)

const awaited = ref<boolean>(true)
const done = ref(false)

function addNextContent(): boolean {
  const nextContent = contentData.value?.shift()
  if (nextContent) {
    setTimeout(() => {
      contentsToDisplay.value.push(nextContent)
    })

    return true
  }

  return false
}

function setElementDone() {
  done.value = true
  aiTemplate.value?.setAnimationActiveChange(false)
  if (props.elementIndex !== undefined) {
    aiTemplate.value?.markElementDisplayed(props.elementIndex)
  }
}

function onContentDone() {
  // Skip animation during streaming; the done signal comes from the streaming-done watcher.
  if (!props.noAnimation && !props.streaming) {
    setTimeout(() => {
      if (!addNextContent()) {
        aiTemplate.value?.setActiveRole(AiRole.user)
        setElementDone()
      }
    }, 50)
  }
}

onMounted(() => {
  if (!props.streaming && contentData.value) {
    aiTemplate.value?.setAnimationActiveChange(true)
    awaited.value = true
    if (props.noAnimation) {
      contentsToDisplay.value = contentData.value.slice()
      contentData.value = []
      setElementDone()
    } else {
      onContentDone()
    }
  }
})

watch(
  () => props.streaming,
  (isStreaming, wasStreaming) => {
    if (isStreaming && !wasStreaming) {
      currentState.value = ''
    }
    if (wasStreaming && !isStreaming) {
      setElementDone()
    }
  }
)

watch(
  () => props.content.length,
  () => {
    if (!props.streaming) {
      return
    }
    const newItem = props.content[props.content.length - 1]
    if (newItem) {
      if (contentData.value === null) {
        contentData.value = []
      }

      currentState.value = newItem.title || ''

      const isThinkingItem = newItem.title === 'thinking'
      const isFinalChunk = newItem.title === 'answer' || newItem.content_type === 'alert'

      // Prune previous thinking items: replace with the latest during thinking,
      // and clear all of them once the final answer/error chunk arrives.
      const shouldPrunePreviousThinking = isThinkingItem || isFinalChunk
      if (shouldPrunePreviousThinking) {
        for (let i = contentData.value.length - 1; i >= 0; i--) {
          if (contentData.value[i]?.title === 'thinking') {
            contentData.value.splice(i, 1)
          }
        }
      }

      contentData.value.push(newItem)
    }
  }
)
</script>

<template>
  <div class="ai-conversation-element" :class="`ai-conversation-element--${role}`">
    <div v-if="role === AiRole.ai" class="ai-conversation-element__ai-header">
      <CmkIcon name="sparkle" size="xlarge" />
      <div class="ai-conversation-element__ai-header-text">
        <CmkHeading type="h2">{{ _t('AI-generated answer') }}</CmkHeading>
        <div v-if="contentData === null" class="ai-conversation-element__loader">
          <CmkIcon name="load-graph" size="large" class="ai-conversation-element__text-loader" />
          <label>{{ loadingText ?? _t('Generating response...') }}</label>
        </div>
        <div v-else-if="currentState === 'thinking'" class="ai-conversation-element__loader">
          <CmkIcon name="load-graph" size="large" class="ai-conversation-element__text-loader" />
          <label>{{ _t('Thinking...') }}</label>
        </div>
        <div v-else class="ai-conversation-element__disclaimer">
          <label>{{ _t('Please review to ensure factual correctness.') }}</label>
        </div>
      </div>
    </div>

    <template v-if="contentData !== null">
      <div v-if="hasDisplayableContent" class="ai-conversation-element__text">
        <template v-for="(cnt, i) in displayItems" :key="i">
          <AlertContent
            v-if="cnt.content_type === 'alert'"
            v-bind="cnt as AlertConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <CodeContent
            v-if="cnt.content_type === 'code'"
            v-bind="cnt as CodeBlockConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <ListContent
            v-else-if="cnt.content_type === 'list'"
            v-bind="cnt as ListConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <DialogContent
            v-else-if="cnt.content_type === 'dialog'"
            v-bind="cnt as DialogConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <ImageContent
            v-else-if="cnt.content_type === 'image'"
            v-bind="cnt as ImageConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <MarkdownContent
            v-else-if="cnt.content_type === 'markdown'"
            v-bind="cnt as MarkdownConversationElementContent"
            :no-animation="props.noAnimation"
            :streaming="props.streaming"
            @done="onContentDone"
          />
        </template>
        <!--
        <div v-if="done && !hideControls" class="ai-conversation-element__ctrls">
          <template v-if="role === AiRole.ai">
            <CmkIconButton name="checkmark"></CmkIconButton>
            <CmkIconButton name="cross"></CmkIconButton>
          </template>
          <template v-if="role === AiRole.user">
            <CmkIconButton name="edit"></CmkIconButton>
          </template>
          <CmkIconButton name="copied"></CmkIconButton>
        </div>
        -->
      </div>
    </template>
  </div>
</template>

<style scoped>
.ai-conversation-element {
  max-width: 100%;
  margin-bottom: var(--dimension-4);
  display: flex;
  flex-direction: row-reverse;
  width: 60%;
  justify-self: flex-end;

  .ai-conversation-element__ai-header {
    display: flex;
    flex-direction: row;
    align-items: center;
    margin-left: var(--dimension-4);

    > img {
      margin-right: var(--dimension-4);
    }

    label {
      opacity: 0.5;
    }

    .ai-conversation-element__ai-header-text {
      display: flex;
      flex-direction: column;
    }
  }

  .ai-conversation-element__loader {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--dimension-4);

    .ai-conversation-element__text-loader {
      animation: rotate 2s linear infinite;
    }
  }

  .ai-conversation-element__text {
    padding: var(--dimension-4);
    background: var(--default-form-element-bg-color);
    border-radius: var(--border-radius);
    border: 1px solid var(--default-border-color);
    display: flex;
    flex-direction: column;
    position: relative;
    margin-bottom: var(--dimension-10);
    margin-left: calc(var(--dimension-4) + var(--dimension-7));

    .ai-conversation-element__text-header {
      width: 100%;
      padding-top: var(--dimension-4);
      margin: var(--dimension-6) 0 var(--dimension-4);
      border-top: 1px solid var(--default-border-color);
    }

    .ai-conversation-element__ctrls {
      position: absolute;
      margin-top: var(--dimension-4);
      display: flex;
      gap: var(--dimension-4);
      justify-content: flex-start;
      bottom: calc(-1 * var(--dimension-8));

      > button {
        opacity: 0.5;

        &:hover {
          opacity: 1;
        }
      }
    }
  }

  &.ai-conversation-element--ai,
  &.ai-conversation-element--system {
    justify-self: flex-start;
    flex-direction: column;
    align-items: start;
    width: 100%;

    .ai-conversation-element__text {
      background: transparent;
      border: none;
      width: calc(100% - (var(--dimension-4) + var(--dimension-7)));
    }
  }

  &.ai-conversation-element--system {
    width: auto;

    .ai-conversation-element__text {
      border: 1px solid var(--default-border-color);
      border-radius: var(--border-radius);
      padding-left: var(--dimension-7);
      padding-right: var(--dimension-7);
      box-sizing: border-box;
    }
  }

  .ai-conversation-element__text-skeleton {
    width: 70%;
    height: 100px;
    margin-bottom: var(--dimension-10);
  }
}
</style>
