<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import { DialogClose, DialogTitle } from 'radix-vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkHeading from './typography/CmkHeading.vue'
import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

const { t } = usei18n('cmk-slide-in')

export interface CmkSlideInDialogProps {
  open: boolean
  header?: {
    title: string
    closeButton: boolean
  }
}
defineProps<CmkSlideInDialogProps>()
const emit = defineEmits(['close'])
</script>

<template>
  <CmkSlideIn :open="open" @close="emit('close')">
    <DialogTitle v-if="header" class="slide-in__title">
      <CmkHeading type="h1">{{ header.title }}</CmkHeading>
      <DialogClose v-if="header.closeButton" class="slide-in__close" @click="emit('close')">
        <CmkIcon :aria-label="t('close-slidein', 'Close')" name="close" size="xsmall" />
      </DialogClose>
    </DialogTitle>

    <CmkScrollContainer type="outer" class="slide-in__content">
      <slot />
    </CmkScrollContainer>
  </CmkSlideIn>
</template>

<style scoped>
.slide-in__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;

  label {
    margin-right: 10px;
  }
}

.slide-in__content {
  padding: 0 20px;
}

.slide-in__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

button {
  margin: 0 10px 0 0;
}
</style>
