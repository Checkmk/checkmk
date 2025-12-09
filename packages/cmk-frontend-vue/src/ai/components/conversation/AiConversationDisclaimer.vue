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

const { _t } = usei18n()
const aiTemplate = getInjectedAiTemplate()
const disclaimerActive = ref<boolean>(false)
const consentTriggered = ref<boolean>(false)
const startButtonDisabled = ref<boolean>(false)

onMounted(async () => {
  if (!aiTemplate.value?.isDisclaimerShown()) {
    disclaimerActive.value = true
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
    v-if="disclaimerActive"
    class="ai-conversation-disclaimer"
    :class="{ 'ai-conversation-disclaimer--triggered': consentTriggered }"
  >
    <CmkHeading type="h1" class="ai-conversation-disclaimer__header">
      {{ _t('Checkmk AI feature usage notice') }}
    </CmkHeading>
    <div class="ai-conversation-disclaimer__element">
      {{
        _t(
          `The feature "Explain with AI" uses a Large Language Model (LLM) [${aiTemplate?.info?.models.join(', ')}] of [${aiTemplate?.info?.provider}] to generate its output. ` +
            'Generated content (output) my contain errors or inaccuracies. ' +
            'Ensure all output generated is carefully reviewed and checked by a human for factual correctness before being used in any way. ' +
            'For further information visit our '
        )
      }}
      <a href="https://docs.checkmk.com/latest" target="_blank">{{ _t('Documentation') }}</a>
      {{ _t('and') }}
      <a href="https://checkmk.com/privacy-policy" target="_blank">{{ _t('Privacy Policy') }}</a
      >.
    </div>

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
    margin: var(--dimension-10) 0;
  }

  .ai-conversation-disclaimer__ctrls {
    display: flex;
    flex-direction: column;
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
