<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Dialog, DialogAction } from 'cmk-shared-typing/typescript/dialog'
import CmkAlert, {
  type CmkAlertOptionalButton,
  type CmkAlertProps
} from 'cmk-ui-library/components/CmkAlert.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import { computed } from 'vue'

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

const optionalButton = computed<CmkAlertOptionalButton | undefined>(() => {
  if (!props.optional_button) {
    return undefined
  }
  if (props.optional_button.dismissal) {
    return {
      title: props.optional_button.title as TranslatedString,
      icon: 'cancel',
      onclick: dismissAlert
    }
  }
  if (props.optional_button.action) {
    return {
      title: props.optional_button.title as TranslatedString,
      onclick: getDialogAction(props.optional_button.action)
    }
  }
  return undefined
})

const alertBoxProps = computed<CmkAlertProps>(() => ({
  text: props.message as TranslatedString,
  ...(props.title ? { heading: props.title as TranslatedString } : {}),
  ...(props.main_button
    ? {
        mainButton: {
          title: props.main_button.title as TranslatedString,
          onclick: getDialogAction(props.main_button.action)
        }
      }
    : {}),
  ...(optionalButton.value ? { optionalButton: optionalButton.value } : {})
}))
</script>

<template>
  <CmkAlert v-if="isShown" v-bind="alertBoxProps" />
</template>
