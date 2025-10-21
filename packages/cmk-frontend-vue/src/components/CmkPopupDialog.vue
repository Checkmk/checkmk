<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { DialogTitle } from 'radix-vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from './CmkButton.vue'
import type { SimpleIcons } from './CmkIcon'
import CmkIcon from './CmkIcon/CmkIcon.vue'
import CmkPopup from './CmkPopup.vue'
import CmkHeading from './typography/CmkHeading.vue'
import CmkParagraph from './typography/CmkParagraph.vue'

const { _t } = usei18n()

export interface CmkPopupDialogProps {
  open: boolean
  icon?: SimpleIcons | undefined
  title: TranslatedString
  text: TranslatedString
  okButtonText?: TranslatedString
}
defineProps<CmkPopupDialogProps>()

const emit = defineEmits(['close'])
</script>

<template>
  <CmkPopup :open="open" @close="emit('close')">
    <CmkIcon class="cmk-popup-dialog__icon" :name="icon ?? 'info-circle'" size="xxxlarge"></CmkIcon>
    <DialogTitle>
      <CmkHeading type="h2" class="cmk-popup-dialog__title">{{ title }}</CmkHeading>
    </DialogTitle>
    <CmkParagraph class="cmk-popup-dialog__text">{{ text }}</CmkParagraph>
    <CmkButton variant="primary" @click="emit('close')">{{ okButtonText ?? _t('OK') }}</CmkButton>
  </CmkPopup>
</template>

<style scoped>
.cmk-popup-dialog__icon,
.cmk-popup-dialog__title,
.cmk-popup-dialog__text {
  margin-bottom: var(--dimension-8);
}
</style>
