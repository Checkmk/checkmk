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

const { isShown, dismiss: dismissAlert } = useDismissDialog(props.optional_button?.dismissal?.key)

const alertBoxProps = computed<CmkAlertBoxProps>(() => {
  const baseProps: CmkAlertBoxProps = {}

  if (props.title) {
    baseProps.heading = props.title
  }

  if (props.main_button) {
    baseProps.mainButton = {
      title: props.main_button.title as TranslatedString,
      onclick: getDialogAction(props.main_button.action)
    }
  }

  if (props.optional_button) {
    if (props.optional_button.dismissal) {
      baseProps.optionalButton = {
        title: props.optional_button.title as TranslatedString,
        icon: 'cancel',
        onclick: dismissAlert
      }
    } else if (props.optional_button.action) {
      baseProps.optionalButton = {
        title: props.optional_button.title as TranslatedString,
        onclick: getDialogAction(props.optional_button.action)
      }
    }
  }

  return baseProps
})
</script>

<template>
  <CmkAlertBox v-if="isShown" v-bind="alertBoxProps">{{ props.message }}</CmkAlertBox>
</template>
