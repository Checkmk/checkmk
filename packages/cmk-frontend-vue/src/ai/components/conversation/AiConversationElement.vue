<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCopy from '@/components/CmkCopy.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
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
  RateLimitConversationElementContent,
  TAiConversationElementContent
} from '@/ai/lib/service/ai-template'
import { loadUserActions } from '@/ai/lib/user-actions'
import { AiRole } from '@/ai/lib/utils'

import AlertContent from './content/AlertContent.vue'
import CodeContent from './content/CodeContent.vue'
import DialogContent from './content/DialogContent.vue'
import ImageContent from './content/ImageContent.vue'
import ListContent from './content/ListContent.vue'
import MarkdownContent from './content/MarkdownContent.vue'
import RateLimitContent from './content/RateLimitContent.vue'

const { _t } = usei18n()
const props = defineProps<IAiConversationElement & { elementIndex?: number }>()
const emit = defineEmits<{ close: [] }>()
const aiTemplate = getInjectedAiTemplate()

function filterThinkingForReopen(
  items: TAiConversationElementContent[]
): TAiConversationElementContent[] {
  const hasAnswer = items.some(
    (c) => c.title === 'answer' || c.content_type === 'alert' || c.content_type === 'rate_limit'
  )
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
const copyableAnswerText = computed(() => {
  const items = Array.isArray(props.content) ? props.content : []
  const chunks: string[] = []

  for (const item of items) {
    if (item.title === 'thinking') {
      continue
    }

    // We can remove unwanted supported content types as needed
    switch (item.content_type) {
      case 'markdown':
        chunks.push(item.content)
        break
      case 'text':
        chunks.push(item.text)
        break
      case 'list':
        chunks.push(item.items.join('\n'))
        break
      case 'code':
        chunks.push(item.code)
        break
    }
  }

  return chunks.join('\n\n').trim()
})
const hasFinalAnswerChunk = computed(() => {
  const items = Array.isArray(props.content) ? props.content : []
  return items.some(
    (item) =>
      item.title === 'answer' || item.content_type === 'alert' || item.content_type === 'rate_limit'
  )
})
const showExtraButtons = computed(
  () =>
    props.role === AiRole.ai &&
    hasFinalAnswerChunk.value &&
    currentState.value !== 'thinking' &&
    copyableAnswerText.value.length > 0
)
const showAiHeader = computed(() => {
  if (props.role !== AiRole.ai) {
    return false
  }

  const currentIndex = props.elementIndex
  if (currentIndex === undefined) {
    return true
  }

  const elements = aiTemplate.value?.elements ?? []
  for (let i = 0; i < elements.length; i++) {
    if (elements[i]?.role === AiRole.ai) {
      return i === currentIndex
    }
  }

  return true
})
const latestAiElement = computed<IAiConversationElement | null>(() => {
  const elements = aiTemplate.value?.elements ?? []
  for (let i = elements.length - 1; i >= 0; i--) {
    if (elements[i]?.role === AiRole.ai) {
      return elements[i] as IAiConversationElement
    }
  }
  return null
})
const latestAiItems = computed(() =>
  Array.isArray(latestAiElement.value?.content) ? latestAiElement.value.content : []
)

const HOST_STATE_LABEL: Record<string, string> = {
  up: 'UP',
  down: 'DOWN',
  unreachable: 'UNREACH'
}

function hostStateLabel(state: string): string {
  return HOST_STATE_LABEL[state.toLowerCase()] ?? state.toUpperCase()
}

function hostStateClass(state: string): string {
  switch (state.toLowerCase()) {
    case 'up':
      return 'hstate hstate0'
    case 'down':
      return 'hstate hstate1'
    case 'unreachable':
      return 'hstate hstate2'
    default:
      return 'hstate hstate3'
  }
}

const SERVICE_STATE_LABEL: Record<string, string> = {
  ok: 'OK',
  warning: 'WARN',
  critical: 'CRIT',
  unknown: 'UNKN',
  pending: 'PEND'
}

function serviceStateLabel(state: string): string {
  return SERVICE_STATE_LABEL[state.toLowerCase()] ?? state.toUpperCase()
}

function serviceStateClass(state: string): string {
  switch (state.toLowerCase()) {
    case 'ok':
      return 'svcstate state0'
    case 'warning':
      return 'svcstate state1'
    case 'critical':
      return 'svcstate state2'
    case 'unknown':
      return 'svcstate state3'
    case 'pending':
      return 'svcstate statep stale'
    default:
      return 'svcstate state3'
  }
}
const isHeaderLoading = computed(
  () => Boolean(latestAiElement.value?.streaming) && latestAiItems.value.length === 0
)
const isHeaderThinking = computed(() => {
  if (!latestAiElement.value?.streaming || latestAiItems.value.length === 0) {
    return false
  }

  return latestAiItems.value[latestAiItems.value.length - 1]?.title === 'thinking'
})
const headerLoadingText = computed(
  () => latestAiElement.value?.loadingText ?? props.loadingText ?? _t('Generating response...')
)

const awaited = ref<boolean>(true)
const done = ref(false)

function resetElementState() {
  currentState.value =
    props.content?.length > 0 ? props.content[props.content.length - 1]?.title || '' : ''
  contentData.value = initContentData()
  contentsToDisplay.value = []
  done.value = false
}

function initializeDisplayState() {
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
}

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

async function onRefresh() {
  const actions = await loadUserActions(aiTemplate.value, { autoExecuteSingleAction: false })
  if (actions instanceof Error) {
    return
  }

  if (actions.length === 1 && actions[0]?.action_id === 'explain_this_service') {
    aiTemplate.value?.refreshUserActionButton(actions[0])
  }
}

onMounted(() => {
  initializeDisplayState()
})

watch(
  () => props.content,
  (newContent, oldContent) => {
    if (newContent === oldContent) {
      return
    }

    resetElementState()
    initializeDisplayState()
  }
)

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
      const isFinalChunk =
        newItem.title === 'answer' ||
        newItem.content_type === 'alert' ||
        newItem.content_type === 'rate_limit'

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
    <div v-if="showAiHeader" class="ai-conversation-element__ai-header">
      <CmkIcon name="sparkle" size="xlarge" />
      <div class="ai-conversation-element__ai-header-text">
        <CmkHeading type="h2">{{ _t('AI-generated answer') }}</CmkHeading>
        <div v-if="isHeaderLoading" class="ai-conversation-element__loader">
          <CmkIcon name="load-graph" size="large" class="ai-conversation-element__text-loader" />
          <label>{{ headerLoadingText }}</label>
        </div>
        <div v-else-if="isHeaderThinking" class="ai-conversation-element__loader">
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
          <RateLimitContent
            v-else-if="cnt.content_type === 'rate_limit'"
            v-bind="cnt as RateLimitConversationElementContent"
            @done="onContentDone"
            @close="emit('close')"
          />
          <div
            v-else-if="cnt.content_type === 'system_context'"
            class="ai-conversation-element__system-context"
          >
            <div class="ai-conversation-element__system-context-card">
              <div class="ai-conversation-element__system-context-card-icon">
                <div class="ai-conversation-element__system-context-card-icon-wrapper">
                  <CmkIcon name="folder" size="large" />
                </div>
              </div>

              <div class="ai-conversation-element__system-context-card-header">
                <span class="ai-conversation-element__system-context-card-label">{{
                  _t('Host')
                }}</span>
                <div class="ai-conversation-element__system-context-card-body">
                  <span
                    :class="[
                      'state',
                      'ai-conversation-element__system-context-state',
                      hostStateClass(cnt.host_state)
                    ]"
                    ><span class="state_rounded_fill">{{
                      hostStateLabel(cnt.host_state)
                    }}</span></span
                  >
                  <span class="ai-conversation-element__system-context-name">{{
                    cnt.host_name
                  }}</span>
                </div>
              </div>
            </div>
            <div v-if="cnt.service_name" class="ai-conversation-element__system-context-card">
              <div class="ai-conversation-element__system-context-card-icon">
                <div class="ai-conversation-element__system-context-card-icon-wrapper">
                  <CmkIcon name="services" size="large" />
                </div>
              </div>
              <div class="ai-conversation-element__system-context-card-header">
                <span class="ai-conversation-element__system-context-card-label">{{
                  _t('Service')
                }}</span>
                <div class="ai-conversation-element__system-context-card-body">
                  <span
                    :class="[
                      'state',
                      'ai-conversation-element__system-context-state',
                      serviceStateClass(cnt.service_state ?? ''),
                      { stale: cnt.is_stale }
                    ]"
                    ><span class="state_rounded_fill">{{
                      serviceStateLabel(cnt.service_state ?? '')
                    }}</span></span
                  >
                  <span class="ai-conversation-element__system-context-name">{{
                    cnt.service_name
                  }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-if="showExtraButtons" class="ai-conversation-element__controls">
          <CmkCopy :text="copyableAnswerText" :copied-message="_t('Copied!')">
            <CmkIconButton
              name="copied"
              size="medium"
              :title="_t('Copy response')"
              class="ai-conversation-element__extra-button ai-conversation-element__extra-button--white"
            />
          </CmkCopy>
          <CmkIconButton
            name="reload"
            size="medium"
            :title="_t('Refresh')"
            class="ai-conversation-element__extra-button ai-conversation-element__extra-button--white"
            @click="onRefresh"
          />
        </div>
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
    display: flex;
    flex-direction: column;
    position: relative;
    margin-bottom: var(--dimension-10);
    margin-left: calc(var(--dimension-4) + var(--dimension-7));

    .ai-conversation-element__controls {
      display: flex;
      justify-content: flex-start;
      margin-top: var(--dimension-4);

      .ai-conversation-element__extra-button {
        border: 1px solid var(--default-component-bg-color);
        border-radius: var(--border-radius);
        background: var(--code-background-color);
        padding: var(--dimension-3);
      }

      .ai-conversation-element__extra-button--white
        /* stylelint-disable-next-line selector-pseudo-class-no-unknown */
      :deep(img) {
        filter: brightness(0) invert(1);
      }
    }

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

  .ai-conversation-element__text-skeleton {
    width: 70%;
    height: 100px;
    margin-bottom: var(--dimension-10);
  }

  .ai-conversation-element__system-context {
    display: flex;
    flex-direction: row;
    gap: calc(2 * var(--dimension-11));
    border-bottom: 1px solid var(--default-border-color);
    padding-bottom: var(--dimension-8);
    border-radius: var(--dimension-2);

    .ai-conversation-element__system-context-card {
      display: flex;
      flex-direction: row;
      padding: var(--dimension-4);
    }

    .ai-conversation-element__system-context-card-icon {
      padding: 0 var(--dimension-4);

      .ai-conversation-element__system-context-card-icon-wrapper {
        background-color: var(--default-form-element-bg-color);
        border: 1px solid var(--default-border-color);
        border-radius: var(--dimension-3);
        padding: var(--dimension-4);
      }
    }

    .ai-conversation-element__system-context-card-header {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--dimension-4);
      font-weight: bold;
    }

    .ai-conversation-element__system-context-card-body {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: var(--dimension-3);

      .ai-conversation-element__system-context-state > span {
        display: inline-block;
        min-width: var(--dimension-11);
        white-space: nowrap;
        text-align: center;
        border: 1px solid var(--default-border-color);
        border-radius: var(--dimension-2);
        text-transform: uppercase;
        padding: var(--dimension-1) var(--dimension-2);
      }
    }

    .ai-conversation-element__system-context-name {
      padding-left: var(--dimension-2);
      font-weight: normal;
    }
  }
}
</style>
