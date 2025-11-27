<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkSkeleton from '@/components/CmkSkeleton.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'
import type { TAiConversationElementContent } from '@/ai/lib/service/ai-template'
import { AiRole } from '@/ai/lib/utils'

import AiConversationElement from './AiConversationElement.vue'

const { _t } = usei18n()
const aiTemplate = getInjectedAiTemplate()
const disclaimerPrompt = ref<TAiConversationElementContent[] | null>(null)
const consentTriggered = ref<boolean>(false)
const startButtonDisabled = ref<boolean>(false)

onMounted(async () => {
  if (!aiTemplate.value?.isDisclaimerShown()) {
    if (typeof aiTemplate.value?.config.getDisclaimer === 'function') {
      try {
        const res = await aiTemplate.value.config.getDisclaimer()
        if (res) {
          disclaimerPrompt.value = res
        }
      } catch {
        startButtonDisabled.value = true
        disclaimerPrompt.value = [
          {
            content_type: 'alert',
            variant: 'error',
            text: _t('Error retrieving AI service information. Please try again later.')
          }
        ]
      }
    }
  }
})

const emit = defineEmits(['consent', 'decline'])

function onConsent() {
  aiTemplate.value?.persistDisclaimerShown()
  consentTriggered.value = true
  emit('consent')
}
</script>

<template>
  <div
    v-if="disclaimerPrompt"
    class="ai-conversation-disclaimer"
    :class="{ 'ai-conversation-disclaimer--triggered': consentTriggered }"
  >
    <CmkHeading type="h1" class="ai-conversation-disclaimer__header">
      {{ _t('Checkmk AI feature documentation & privacy policy') }}
    </CmkHeading>
    <AiConversationElement
      :role="AiRole.system"
      :content="disclaimerPrompt"
      :no-animation="true"
      :hide-controls="true"
      class="ai-conversation-disclaimer__element"
    />

    <div v-if="!consentTriggered" class="ai-conversation-disclaimer__ctrls">
      <div>
        <CmkButton variant="primary" :disabled="startButtonDisabled" @click="onConsent">
          {{ _t('Start AI feature') }}
        </CmkButton>
        <CmkButton @click="emit('decline')">{{ _t('Cancel and go back') }}</CmkButton>
      </div>
    </div>
  </div>
  <CmkSkeleton v-else class="ai-conversation-disclaimer__skeleton" />
</template>

<style scoped>
.ai-conversation-disclaimer {
  width: 95%;
  position: absolute;
  margin-top: var(--dimension-10);
  margin-bottom: var(--dimension-8);
  overflow: hidden;

  &.ai-conversation-disclaimer--triggered {
    opacity: 0;
    transition: opacity 0.5s ease-in-out;
  }

  .ai-conversation-disclaimer {
    width: 100%;
    text-align: left;
    display: flex;
    flex-direction: column;
    align-items: start;
    padding-left: var(--dimension-4);
    gap: var(--dimension-5);
  }

  .ai-conversation-disclaimer__element {
    margin: var(--dimension-10) 0 0 -28px;
  }

  .ai-conversation-disclaimer__ctrls {
    display: flex;
    flex-direction: column;
    padding-left: var(--dimension-4);
    margin-bottom: var(--dimension-8);
    align-items: start;
    justify-content: start;
    gap: var(--dimension-4);

    > div {
      display: flex;
      align-items: center;
      flex-direction: row;
      gap: var(--dimension-4);
    }
  }
}

.ai-conversation-disclaimer__skeleton {
  width: 70%;
  height: 100px;
}
</style>
