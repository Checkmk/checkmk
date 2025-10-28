<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import type { AiConversationBaseTemplate } from '@/ai/lib/conversation-templates/base-template'

import AiConversation from './AiConversation.vue'

const aiTemplate = defineModel<AiConversationBaseTemplate>({ required: true })
const props = defineProps<{
  title: TranslatedString
}>()

const slideInOpen = defineModel<boolean>('slidoeut-open', { required: true })

function onClose() {
  slideInOpen.value = false
}
</script>

<template>
  <CmkSlideInDialog
    :header="{
      title: props.title,
      icon: {
        name: 'sparkle',
        size: 'xlarge'
      },
      closeButton: true
    }"
    :open="slideInOpen"
    @close="onClose"
  >
    <AiConversation v-if="slideInOpen" v-model="aiTemplate" @close="onClose" />
  </CmkSlideInDialog>
</template>
