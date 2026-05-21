<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Dialog, DialogAction } from 'cmk-shared-typing/typescript/dialog'
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import { useDismissDialog } from '@/lib/useDismissDialog'

import CmkAlertBox, { type CmkAlertBoxProps } from '@/components/CmkAlertBox.vue'

const props = defineProps<Dialog>()

function getDialogAction(action: DialogAction): () => void {
  if (action.type === 'redirect') {
    return () => {
      window.location.href = action.url
    }
  }
  throw new Error(`Unknown action: ${action.type}`)
}

const { isShown: dismissalShown, dismiss: dismissAlert } = useDismissDialog(
  props.dismissal_button?.key
)

const alertBoxProps = computed<CmkAlertBoxProps>(() => {
  const baseProps: CmkAlertBoxProps = {}

  if (props.title) {
    baseProps.heading = props.title
  }

  const allButtons = (props.buttons ?? []).map((button) => ({
    title: button.title as TranslatedString,
    variant: button.variant,
    onclick: getDialogAction(button.action)
  }))

  if (props.dismissal_button) {
    allButtons.push({
      title: props.dismissal_button.title as TranslatedString,
      variant: 'optional' as const,
      onclick: dismissAlert
    })
  }

  if (allButtons.length) {
    baseProps.buttons = allButtons
  }

  return baseProps
})
</script>

<template>
  <CmkAlertBox v-if="dismissalShown" v-bind="alertBoxProps">{{ props.message }}</CmkAlertBox>
</template>
