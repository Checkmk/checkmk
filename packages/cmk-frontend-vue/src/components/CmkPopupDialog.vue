<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogTitle } from 'radix-vue'

import CmkButton from './CmkButton.vue'
import CmkPopup from './CmkPopup.vue'

export interface CmkPopupDialogProps {
  open: boolean
  title: string
  text?: string
  okButtonText?: string | undefined
  stayOpenOverlayClick?: boolean
}
defineProps<CmkPopupDialogProps>()

const emit = defineEmits(['close'])
</script>

<template>
  <CmkPopup :open="open" @close="!stayOpenOverlayClick && emit('close')">
    <DialogTitle>
      <div class="cmk-popup-dialog__title">{{ title }}</div>
    </DialogTitle>
    <slot> </slot>
    <p v-if="text" class="cmk-popup-dialog__text">{{ text }}</p>

    <CmkButton v-if="okButtonText !== undefined" variant="primary" @click="emit('close')">{{
      okButtonText
    }}</CmkButton>
  </CmkPopup>
</template>

<style scoped>
.cmk-popup-dialog__icon,
.cmk-popup-dialog__title,
.cmk-popup-dialog__text {
  margin-bottom: 24px;
  font-size: small;
}
</style>
