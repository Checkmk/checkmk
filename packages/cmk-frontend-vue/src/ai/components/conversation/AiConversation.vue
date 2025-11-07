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

import AiConversationConsent from './AiConversationConsent.vue'
import AiConversationElement from './AiConversationElement.vue'

const aiTemplate = getInjectedAiTemplate()

const showConsent = ref<boolean>(!aiTemplate.value?.isConsented())

const emit = defineEmits(['close', 'consent'])

const elements = computed(() => aiTemplate.value?.elements as unknown as IAiConversationElement[])
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
    scrollContainer.scrollTo({ top: scrollContainer.offsetHeight, behavior: 'smooth' })
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
}

function onConsent() {
  setTimeout(() => {
    aiTemplate.value?.onAnimationActiveChange(onAnimationActiveChange)
    showConsent.value = false
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
      <AiConversationElement v-for="(element, index) in elements" :key="index" v-bind="element" />
      <AiUserAction v-if="aiTemplate?.activeRole === AiRole.user" />
    </template>
  </div>
  <div ref="automatic-scroll-to" class="ai-conversation__auto-scroll-el"></div>
</template>

<style scoped>
.ai-conversation {
  width: 100%;
  position: relative;

  .ai-conversation__auto-scroll-el {
    position: relative;
    width: 100%;
    height: var(--dimension-10);
  }
}
</style>
