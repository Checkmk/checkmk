<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type {
  AlertConversationElementContent,
  CodeBlockConversationElementContent,
  DialogConversationElementContent,
  IAiConversationElement,
  ImageConversationElementContent,
  ListConversationElementContent,
  TAiConversationElementContent,
  TextConversationElementContent
} from '@/ai/lib/conversation-templates/base-template'
import { AiRole } from '@/ai/lib/utils'

import AlertContent from './content/AlertContent.vue'
import CodeContent from './content/CodeContent.vue'
import DialogContent from './content/DialogContent.vue'
import ImageContent from './content/ImageContent.vue'
import ListContent from './content/ListContent.vue'
import TextContent from './content/TextContent.vue'

const { _t } = usei18n()
const props = defineProps<IAiConversationElement>()

const contentData = ref<TAiConversationElementContent[] | null>(
  typeof props.content === 'function' || props.content instanceof Promise ? null : props.content
)

const contentsToDisplay = ref<TAiConversationElementContent[]>([])

const awaited = ref<boolean>(props.content instanceof Promise ? false : true)
const done = ref(false)

function addNextContent(): boolean {
  const nextContent = contentData.value?.shift()
  if (nextContent) {
    contentsToDisplay.value.push(nextContent)

    return true
  }

  return false
}

function onContentDone() {
  if (!props.noAnimation) {
    setTimeout(() => {
      if (!addNextContent()) {
        done.value = true
      }
    }, 50)
  }
}

const rolename = computed(() => {
  switch (props.role) {
    case AiRole.user:
      return 'You'
    case AiRole.ai:
      return 'AI'
    default:
      return 'System'
  }
})

onMounted(async () => {
  if (typeof props.content === 'function') {
    contentData.value = await props.content()
  } else if (props.content instanceof Promise) {
    contentData.value = await props.content
  }
  awaited.value = true
  if (props.noAnimation) {
    contentsToDisplay.value = contentData.value ?? []
  } else {
    onContentDone()
  }
})
</script>

<template>
  <div class="ai-conversation-element" :class="`ai-conversation-element--${role}`">
    <template v-if="contentData === null">
      <div class="ai-conversation-element__loader">
        <CmkIcon name="load-graph" size="xlarge" class="ai-conversation-element__text-loader" />
        <label>{{ loadingText ?? _t('Generating response...') }}</label>
      </div>
    </template>
    <template v-else>
      <div class="ai-conversation-element__avatar">
        <strong>{{ rolename }}</strong>
      </div>
      <div v-if="contentData" class="ai-conversation-element__text">
        <template v-for="(cnt, i) in contentsToDisplay" :key="i">
          <CmkHeading
            v-if="cnt.title && cnt.type !== 'dialog'"
            class="ai-conversation-element__text-header"
            type="h2"
          >
            {{ cnt.title }}
          </CmkHeading>
          <AlertContent
            v-if="cnt.type === 'alert'"
            v-bind="cnt as AlertConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <TextContent
            v-if="cnt.type === 'text'"
            v-bind="cnt as TextConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <CodeContent
            v-else-if="cnt.type === 'code'"
            v-bind="cnt as CodeBlockConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <ListContent
            v-else-if="cnt.type === 'list'"
            v-bind="cnt as ListConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <DialogContent
            v-else-if="cnt.type === 'dialog'"
            v-bind="cnt as DialogConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
          <ImageContent
            v-else-if="cnt.type === 'image'"
            v-bind="cnt as ImageConversationElementContent"
            :no-animation="props.noAnimation"
            @done="onContentDone"
          />
        </template>
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
  gap: var(--dimension-6);
  width: 60%;

  .ai-conversation-element__loader {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: var(--dimension-4);

    .ai-conversation-element__text-loader {
      animation: rotate 2s linear infinite;
    }
  }

  .ai-conversation-element__avatar {
    background: var(--default-form-element-bg-color);
    border-radius: 50%;
    width: var(--dimension-10);
    height: var(--dimension-10);
    display: flex;
    align-items: center;
    justify-content: center;
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

    .ai-conversation-element__text-header {
      width: 100%;
      padding-bottom: var(--dimension-4);
      margin: var(--dimension-6) 0 var(--dimension-4);
      border-bottom: 1px solid var(--default-border-color);
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
    flex-direction: column;
    align-items: start;
    width: 100%;

    .ai-conversation-element__text {
      background: transparent;
      border: none;
      width: 90%;
    }

    .ai-conversation-element__avatar {
      display: none;
    }
  }

  .ai-conversation-element__text-skeleton {
    width: 70%;
    height: 100px;
    margin-bottom: var(--dimension-10);
  }
}
</style>
