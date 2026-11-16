<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert, { type CmkAlertProps } from 'cmk-ui-library/components/CmkAlert.vue'
import { computed } from 'vue'

import type { ActionFeedbackEntry } from './types'

const props = defineProps<{
  feedback: ActionFeedbackEntry
}>()

const open = defineModel<boolean>('open', { default: false })

const alertProps = computed<CmkAlertProps>(() => {
  const { feedback } = props
  // An action still running can be neither closed nor done with.
  if (feedback.variant === 'loading') {
    return { variant: 'loading', text: feedback.message }
  }
  const { variant, heading, message } = feedback
  if (variant === 'success') {
    return { variant, dismissible: true, autoDismiss: true, heading, text: message }
  }
  if (variant === 'warning') {
    return { variant, dismissible: true, heading, text: message }
  }
  return { variant, heading, text: message }
})
</script>

<template>
  <CmkAlert v-bind="alertProps" v-model:open="open" />
</template>
