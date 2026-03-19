<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useTemplateRef } from 'vue'

import AiUserAction from '@/ai/components/user-action/AiConversationUserAction.vue'
import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'
import type { IAiConversationElement } from '@/ai/lib/service/ai-template'
import { AiRole } from '@/ai/lib/utils'

import AiConversationConsent from './AiConversationDisclaimer.vue'
import AiConversationElement from './AiConversationElement.vue'
import AiConversationFooter from './AiConversationFooter.vue'

const aiTemplate = getInjectedAiTemplate()

const showConsent = ref<boolean>(!aiTemplate.value?.isDisclaimerShown())

const emit = defineEmits(['close', 'consent'])

const elements = computed(() => aiTemplate.value?.elements as unknown as IAiConversationElement[])
const showUserActions = computed(
  () => !aiTemplate.value?.elements.some((e) => e.role === AiRole.ai)
)
const scrollInterval = ref<ReturnType<typeof setInterval> | null>(null)
const scrollToRef = useTemplateRef('automatic-scroll-to')

function clearScrollInterval() {
  setTimeout(() => {
    if (typeof scrollInterval.value === 'number') {
      clearInterval(scrollInterval.value)
      scrollInterval.value = null
    }
  }, 1000)
}

function scrollBottom() {
  const scrollContainer = scrollToRef.value?.closest(
    '.cmk-slide-in-dialog__content'
  ) as HTMLDivElement
  if (scrollContainer) {
    // Check if user is near the bottom (within 150px)
    // Only auto-scroll if they haven't manually scrolled up
    const isNearBottom =
      scrollContainer.scrollHeight - scrollContainer.scrollTop - scrollContainer.clientHeight < 150

    // Use scrollHeight to get the total content height (visible height)
    if (isNearBottom) {
      scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' })
    }
  }
}

function forceScrollBottom() {
  // Force scroll to bottom regardless of user's scroll position
  // Used when initially opening dialog
  const scrollContainer = scrollToRef.value?.closest(
    '.cmk-slide-in-dialog__content'
  ) as HTMLDivElement
  if (scrollContainer) {
    scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' })
  }
}

function onAnimationActiveChange(active: boolean) {
  if (active) {
    if (scrollInterval.value === null) {
      scrollInterval.value = setInterval(scrollBottom, 200)
    }
  } else {
    clearScrollInterval()
  }
}

if (!showConsent.value) {
  aiTemplate.value?.onAnimationActiveChange(onAnimationActiveChange)
  // Scroll to bottom immediately when opening with existing content
  setTimeout(() => forceScrollBottom(), 100)
}

function onConsent() {
  setTimeout(() => {
    aiTemplate.value?.onAnimationActiveChange(onAnimationActiveChange)
    showConsent.value = false
    // Scroll to bottom after consent is given and content appears
    setTimeout(() => forceScrollBottom(), 100)
  }, 500)
}

function onDecline() {
  emit('close')
}

onBeforeUnmount(() => {
  clearScrollInterval()
})
</script>

<template>
  <div class="ai-conversation">
    <AiConversationConsent v-if="showConsent" @consent="onConsent" @decline="onDecline" />
    <template v-else>
      <AiConversationElement
        v-for="(element, index) in elements"
        :key="index"
        :element-index="index"
        v-bind="element"
      />
      <AiUserAction v-if="showUserActions" />
    </template>
    <div ref="automatic-scroll-to" class="ai-conversation__auto-scroll-el"></div>
  </div>
  <AiConversationFooter />
</template>

<style scoped>
.ai-conversation {
  width: 100%;
  position: relative;
  margin-bottom: calc(var(--dimension-10) + var(--dimension-8));

  .ai-conversation__auto-scroll-el {
    position: relative;
    width: 100%;
    height: var(--dimension-10);
  }
}
</style>
