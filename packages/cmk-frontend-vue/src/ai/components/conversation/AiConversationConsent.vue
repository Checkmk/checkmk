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
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'
import type { TAiConversationElementContent } from '@/ai/lib/service/ai-template'
import { AiRole } from '@/ai/lib/utils'

import AiConversationElement from './AiConversationElement.vue'

const { _t } = usei18n()
const aiTemplate = getInjectedAiTemplate()
const systemPromp = ref<TAiConversationElementContent[] | null>(null)
const doNotAskAgain = ref<boolean>(false)
const consentTriggered = ref<boolean>(false)

onMounted(async () => {
  if (!aiTemplate.value?.isConsented()) {
    if (typeof aiTemplate.value?.config.dataToProvideToLlm === 'function') {
      const res = await aiTemplate.value.config.dataToProvideToLlm()
      if (res) {
        systemPromp.value = res
      }
    }
  }
})

const emit = defineEmits(['consent', 'decline'])

function onConsent() {
  if (doNotAskAgain.value) {
    aiTemplate.value?.persistConsent()
  }
  consentTriggered.value = true
  emit('consent')
}
</script>

<template>
  <div
    v-if="systemPromp"
    class="ai-conversation-consent"
    :class="{ 'ai-conversation-consent--triggered': consentTriggered }"
  >
    <CmkHeading type="h1" class="ai-conversation-consent__header">
      {{ _t('Continue with AI?') }}
    </CmkHeading>
    <AiConversationElement
      :role="AiRole.system"
      :content="systemPromp"
      :no-animation="true"
      :hide-controls="true"
    />

    <div v-if="!consentTriggered" class="ai-conversation-consent__ctrls">
      <CmkCheckbox v-model="doNotAskAgain" :label="_t('Do not ask again')" />
      <div>
        <CmkButton variant="primary" @click="onConsent">
          {{ _t('Confirm & proceed') }}
        </CmkButton>
        <CmkButton @click="emit('decline')">{{ _t('Decline') }}</CmkButton>
      </div>
    </div>
  </div>
  <CmkSkeleton v-else class="ai-conversation-consent__skeleton" />
</template>

<style scoped>
.ai-conversation-consent {
  width: 95%;
  position: absolute;
  margin-top: var(--dimension-10);
  margin-bottom: var(--dimension-8);
  overflow: hidden;

  &.ai-conversation-consent--triggered {
    opacity: 0;
    transition: opacity 0.5s ease-in-out;
  }

  .ai-conversation-consent__header {
    width: 100%;
    text-align: left;
    display: flex;
    flex-direction: column;
    align-items: start;
    padding-left: var(--dimension-4);
    gap: var(--dimension-5);
  }

  .ai-conversation-consent__ctrls {
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

.ai-conversation-consent__skeleton {
  width: 70%;
  height: 100px;
}
</style>
