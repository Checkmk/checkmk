<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert, { type CmkAlertProps } from 'cmk-ui-library/components/CmkAlert.vue'
import { computed } from 'vue'

import type { ActionOutcome } from './types'

const props = defineProps<{
  feedback: ActionOutcome
}>()

const open = defineModel<boolean>('open', { default: false })

const alertProps = computed<CmkAlertProps>(() =>
  props.feedback.variant === 'success'
    ? {
        variant: 'success',
        dismissible: true,
        autoDismiss: true,
        heading: props.feedback.heading,
        text: props.feedback.message
      }
    : { variant: 'error', heading: props.feedback.heading, text: props.feedback.message }
)
</script>

<template>
  <CmkAlert v-bind="alertProps" v-model:open="open" />
</template>
