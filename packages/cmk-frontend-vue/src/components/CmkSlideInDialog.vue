<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogClose, DialogTitle } from 'radix-vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkHeading from './typography/CmkHeading.vue'

const { _t } = usei18n()

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
    <DialogTitle v-if="header" class="cmk-slide-in-dialog__title">
      <CmkHeading type="h1">{{ header.title }}</CmkHeading>
      <DialogClose
        v-if="header.closeButton"
        class="cmk-slide-in-dialog__close"
        @click="emit('close')"
      >
        <CmkIcon :aria-label="_t('Close')" name="close" size="xsmall" />
      </DialogClose>
    </DialogTitle>

    <CmkScrollContainer type="outer" class="cmk-slide-in-dialog__content">
      <slot />
    </CmkScrollContainer>
  </CmkSlideIn>
</template>

<style scoped>
.cmk-slide-in-dialog__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px;

  label {
    margin-right: 10px;
  }
}

.cmk-slide-in-dialog__content {
  padding: 0 20px;
}

.cmk-slide-in-dialog__close {
  background: none;
  border: none;
  margin: 0;
  padding: 0;
}

button {
  margin: 0 10px 0 0;
}
</style>
