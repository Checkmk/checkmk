<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import type {
  AiConversationBaseTemplate,
  IAiConversationElement
} from '@/ai/lib/conversation-templates/base-template'

import AiConversationConsent from './AiConversationConsent.vue'
import AiConversationElement from './AiConversationElement.vue'

const aiTemplate = defineModel<AiConversationBaseTemplate>({ required: true })

const showConsent = ref<boolean>(!aiTemplate.value.consented.value)
const emit = defineEmits(['close', 'consent'])

const elements = computed(() => aiTemplate.value.elements as unknown as IAiConversationElement[])

function onConsent() {
  setTimeout(() => {
    showConsent.value = false
  }, 500)
}

function onDecline() {
  emit('close')
}
</script>

<template>
  <div class="ai-conversation">
    <AiConversationConsent
      v-if="showConsent"
      v-model="aiTemplate"
      @consent="onConsent"
      @decline="onDecline"
    />
    <template v-else>
      <AiConversationElement v-for="(element, index) in elements" :key="index" v-bind="element" />
    </template>
  </div>
</template>

<style scoped>
.ai-conversation {
  width: 100%;
  position: relative;
}
</style>
