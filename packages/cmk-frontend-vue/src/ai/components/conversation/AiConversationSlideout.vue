<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import AiConversation from './AiConversation.vue'

const props = defineProps<{
  title: TranslatedString
}>()

const slideInOpen = defineModel<boolean>('slideout-open', { required: true })

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
    size="small"
    :open="slideInOpen"
    @close="onClose"
  >
    <AiConversation v-if="slideInOpen" @close="onClose" />
  </CmkSlideInDialog>
</template>
