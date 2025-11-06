<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

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
    <AiConversationConsent v-if="showConsent" @consent="onConsent" @decline="onDecline" />
    <template v-else>
      <AiConversationElement v-for="(element, index) in elements" :key="index" v-bind="element" />
      <AiUserAction v-if="aiTemplate?.activeRole === AiRole.user" />
    </template>
  </div>
</template>

<style scoped>
.ai-conversation {
  width: 100%;
  position: relative;
}
</style>
