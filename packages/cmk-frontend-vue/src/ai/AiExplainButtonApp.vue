<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type AiButton, type ExplainThisIssueData } from 'cmk-shared-typing/typescript/ai_button'
import { type Ref, computed, provide, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import AiConversationSlideout from './components/conversation/AiConversationSlideout.vue'
import { aiTemplateKey } from './lib/provider/ai-template'
import { AiTemplateService } from './lib/service/ai-template'

const props = defineProps<AiButton>()
const aiTemplate = ref<AiTemplateService | null>(null)

provide(aiTemplateKey, aiTemplate as Ref<AiTemplateService | null>)

const conversationOpen = ref(false)

function explainThis() {
  // Only create a new service instance if one doesn't exist yet
  // This ensures conversation data persists when the dialog is closed and reopened
  if (aiTemplate.value === null) {
    aiTemplate.value = new AiTemplateService(
      props.template.id,
      props.user_id,
      props.template.context_data,
      props.site_name
    )
  } else {
    // When reopening, disable animations on all existing elements
    aiTemplate.value.disableAllAnimations()
  }
  conversationOpen.value = true
}

const templateLoaded = computed(() => {
  return aiTemplate.value !== null
})

function isSameContext(a: ExplainThisIssueData, b: ExplainThisIssueData): boolean {
  return (
    a.host_name === b.host_name &&
    a.service_name === b.service_name &&
    a.service_state === b.service_state &&
    a.host_state === b.host_state
  )
}

// Listen for events from both icon clicks and button clicks
// Icon clicks (from explain_with_ai.py) include context data in event.detail
// Button clicks trigger without detail, using the component's props instead
document.addEventListener('cmk-ai-explain-button', (event: Event) => {
  const customEvent = event as CustomEvent<ExplainThisIssueData | undefined>
  if (customEvent.detail) {
    // Event from icon: use the provided context data
    const incoming = customEvent.detail
    if (aiTemplate.value !== null && isSameContext(aiTemplate.value.context_data, incoming)) {
      // same context: reopen the existing conversation
      aiTemplate.value.disableAllAnimations()
    } else {
      // different context: start fresh
      aiTemplate.value = new AiTemplateService(
        props.template.id,
        props.user_id,
        incoming,
        props.site_name
      )
    }
    conversationOpen.value = true
  } else {
    // Event from button: use component props
    explainThis()
  }
})
</script>

<template>
  <AiConversationSlideout
    v-if="templateLoaded"
    :slideout-open="conversationOpen"
    :title="props.template.title as TranslatedString"
    @update:slideout-open="
      (value) => {
        conversationOpen = value
      }
    "
  />

  <Teleport v-if="templateLoaded && !conversationOpen" defer to=".main">
    <div class="ai-explain-button-app__tooltip-wrapper">
      <button
        type="button"
        class="ai-explain-button-app__tooltip-button"
        role="button"
        @click="explainThis"
      >
        {{ button_text }}
        <CmkIcon name="sparkle-white" size="xlarge" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.ai-explain-button-app__tooltip-wrapper {
  position: absolute;
  top: calc(50% - 20px);
  right: 0;
  height: 40px;
  width: 30px;
  overflow: hidden;
  z-index: var(--z-index-ai-tooltip);
  transition: width 0.3s ease;

  &:hover {
    width: 170px;
  }
}

.ai-explain-button-app__tooltip-button {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  position: absolute;
  top: 0;
  left: 0;
  margin-left: 0;
  height: 100%;
  width: 170px;
  padding: 4px 8px 4px 12px;
  border: none;
  border-radius: 25px 0 0 25px;
  background-color: var(--color-purple-60);
  box-sizing: border-box;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
  color: var(--color-white-100);

  &::before {
    display: inline-block;
    padding: 3px;
    border: solid var(--color-white-100);
    border-width: 0 3px 3px 0;
    border-radius: 0 0 2px;
    transform: rotate(135deg);
    content: '';
  }
}

.ai-explain-button-app__button {
  height: 30px;
  margin: 3px 0;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--ux-theme-5) !important;

  .ai-explain-button-app__shimmer {
    width: 100%;
    height: 100%;
    position: absolute;
    inset: 0;
    transform: translateX(-100%);
    opacity: 0.2;
    background: linear-gradient(
      90deg,
      transparent 0,
      var(--color-purple-80) 20%,
      var(--color-purple-60) 60%,
      transparent
    );
    animation: shimmer 3s infinite;
  }

  img {
    margin-right: var(--dimension-3);
  }
}

@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>
