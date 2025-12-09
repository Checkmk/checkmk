<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkSkeleton from '@/components/CmkSkeleton.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import AlertContent from '@/ai/components/conversation/content/AlertContent.vue'
import { getInjectedAiTemplate } from '@/ai/lib/provider/ai-template'
import type { AiActionButton } from '@/ai/lib/service/ai-template'

import AiConversationUserActionButton from './AiConversationUserActionButton.vue'

const { _t } = usei18n()
const aiTemplate = getInjectedAiTemplate()
const actionsError = ref<Error | null>(null)
const userActions = ref<AiActionButton[] | null>(null)

async function loadUserActions() {
  const actions = await aiTemplate.value?.getUserActionButtons()
  if (actions instanceof Error) {
    actionsError.value = actions
  } else {
    if (!actions) {
      userActions.value = []
    } else {
      userActions.value = actions
    }
  }
}

onMounted(async () => {
  await loadUserActions()
})
</script>

<template>
  <div class="ai-conversation-user-action__container">
    <CmkHeading v-if="userActions && userActions.filter((a) => !a.executed).length > 0" type="h4">{{
      _t('What would you like the AI to do?')
    }}</CmkHeading>
    <template v-if="userActions">
      <AiConversationUserActionButton
        v-for="action in userActions.filter((a) => !a.executed)"
        :key="action.action_id"
        v-bind="action"
        @click="aiTemplate?.execUserActionButton(action)"
      />
    </template>
    <template v-else-if="!actionsError">
      <CmkSkeleton v-for="i in 3" :key="i" class="ai-conversation-user-action__skeleton" />
    </template>
    <template v-if="userActions && userActions.length === 0">
      <AlertContent content_type="alert" variant="warning" :text="_t('No actions found')" />
    </template>
    <template v-else-if="actionsError">
      <AlertContent
        content_type="alert"
        variant="error"
        :text="_t('Error retrieving available AI actions. Please try again later.')"
        :title="actionsError.name"
      />
    </template>
    <br />
  </div>
</template>

<style scoped>
.ai-conversation-user-action__container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-self: flex-end;
  gap: var(--dimension-5);

  button {
    gap: var(--dimension-4);
    display: flex;
    justify-content: flex-start;
  }

  .ai-conversation-user-action__skeleton {
    width: 180px;
    height: 30px;
    border-radius: var(--border-radius);
  }
}
</style>
