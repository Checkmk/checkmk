<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type AiButton } from 'cmk-shared-typing/typescript/ai_button'
import { type Ref, computed, provide, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import AiConversationSlideout from './components/conversation/AiConversationSlideout.vue'
import { aiTemplateKey } from './lib/provider/ai-template'
import { AiTemplateService } from './lib/service/ai-template'

const props = defineProps<AiButton>()
const aiTemplate = ref<AiTemplateService | null>(null)

provide(aiTemplateKey, aiTemplate as Ref<AiTemplateService | null>)

const conversationOpen = ref(true)

function explainThis() {
  aiTemplate.value = new AiTemplateService(
    props.template.id,
    props.user_id,
    props.template.context_data
  )
  conversationOpen.value = true
}

const templateLoaded = computed(() => {
  return aiTemplate.value !== null
})

document.addEventListener('cmk-ai-explain-button', () => {
  explainThis()
})
</script>

<template>
  <div id="ai-explain-button"></div>
  <Teleport v-if="props.hide_button !== true" defer :to="teleport ?? '#ai-explain-button'">
    <CmkButton class="ai-explain-button-app__button" @click="explainThis">
      <div class="ai-explain-button-app__shimmer"></div>
      <CmkIcon name="sparkle" />
      {{ button_text }}
    </CmkButton>
  </Teleport>

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
</template>

<style scoped>
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
