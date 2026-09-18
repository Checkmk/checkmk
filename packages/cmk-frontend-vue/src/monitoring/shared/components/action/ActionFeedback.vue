<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox, { type CmkAlertBoxProps } from 'cmk-ui-library/components/CmkAlertBox.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

export interface ActionFeedback {
  variant: 'success' | 'error'
  message: TranslatedString
  heading?: TranslatedString
}

const props = defineProps<{
  feedback: ActionFeedback
}>()

const open = defineModel<boolean>('open', { default: false })

const alertProps = computed<CmkAlertBoxProps>(() =>
  props.feedback.variant === 'success'
    ? { variant: 'success', dismissible: true, autoDismiss: true, heading: props.feedback.heading }
    : { variant: 'error', heading: props.feedback.heading }
)
</script>

<template>
  <CmkAlertBox v-bind="alertProps" v-model:open="open">{{ feedback.message }}</CmkAlertBox>
</template>
