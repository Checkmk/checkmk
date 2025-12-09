<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkSkeleton from '@/components/CmkSkeleton.vue'

import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'

const { _t } = usei18n()
const aiTemplate = getInjectedAiTemplate()

const aiInfo = ref<string | null>(null)

aiTemplate.value?.onInfoLoaded(() => {
  if (aiTemplate.value?.info) {
    aiInfo.value = _t(
      `This feature uses ${aiTemplate.value.info.models.join(', ')} by ${aiTemplate.value.info.provider}. ` +
        'The generated output can contain errors or inaccuracies and must be carefully reviewed by a human for factual correctness. '
    )
  }
})
</script>

<template>
  <div class="ai-conversation-footer">
    <template v-if="aiInfo">
      <span>{{ aiInfo }}</span>
      <a href="https://docs.checkmk.com" target="_blank">{{ _t('Documentation') }}</a>
      {{ _t('and') }}
      <a href="https://checkmk.com/privacy-policy" target="_blank">{{ _t('Privacy Policy') }}</a>
    </template>
    <CmkSkeleton v-else type="info-text" class="ai-conversation-footer__skeleton"></CmkSkeleton>
  </div>
</template>

<style scoped>
.ai-conversation-footer {
  position: absolute;
  bottom: 0;
  height: var(--dimension-10);
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--default-border-color);
  font-size: var(--font-size-small);
  margin-right: var(--dimension-9);
  width: calc(100% - 2 * var(--dimension-7));
  background: var(--default-bg-color);
  color: var(--font-color-dimmed);

  .ai-conversation-footer__skeleton {
    width: 100%;
  }

  a {
    color: var(--font-color-dimmed) !important;
  }
}
</style>
