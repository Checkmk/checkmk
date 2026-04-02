<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import type {
  RateLimitConversationElementContent,
  TBaseConversationElementEmits
} from '@/ai/lib/service/ai-template'

defineProps<RateLimitConversationElementContent>()

const { _t } = usei18n()

const emit = defineEmits<TBaseConversationElementEmits & { close: [] }>()

onMounted(() => {
  emit('done')
})
</script>

<template>
  <div class="ai-rate-limit-content" data-testid="ai-rate-limit-content">
    <CmkIcon name="unavailable" size="xxxlarge" />
    <h3 class="ai-rate-limit-content__title">{{ _t('Feature temporarily unavailable') }}</h3>
    <p class="ai-rate-limit-content__message">
      {{ _t('We are currently experiencing high load. Please try again later.') }}
    </p>
    <CmkButton variant="primary" @click="emit('close')">{{ _t('Close') }}</CmkButton>
  </div>
</template>

<style scoped>
.ai-rate-limit-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-6);
  padding: var(--dimension-10) var(--dimension-8);
  text-align: center;

  .ai-rate-limit-content__title {
    font-size: var(--font-size-large);
    font-weight: bold;
    margin: 0;
  }

  .ai-rate-limit-content__message {
    margin: 0;
    opacity: 0.8;
    max-width: 320px;
  }
}
</style>
