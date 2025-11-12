<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Dialog, DialogAction } from 'cmk-shared-typing/typescript/dialog'
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CmkDialog, { type CmkDialogProps } from '@/components/CmkDialog.vue'

const props = defineProps<Dialog>()

function getDialogAction(action: DialogAction): () => void {
  if (action.type === 'redirect') {
    return () => {
      window.location.href = action.url
    }
  }
  throw new Error(`Unknown action: ${action.type}`)
}

const dialogProps = computed<CmkDialogProps>(() => {
  const baseProps: CmkDialogProps = {
    message: props.message as TranslatedString
  }

  if (props.title) {
    baseProps.title = props.title as TranslatedString
  }

  if (props.buttons) {
    baseProps.buttons = props.buttons.map((button) => ({
      title: button.title as TranslatedString,
      variant: button.variant,
      onclick: getDialogAction(button.action)
    }))
  }

  if (props.dismissal_button) {
    baseProps.dismissal_button = {
      title: props.dismissal_button.title as TranslatedString,
      key: props.dismissal_button.key
    }
  }

  return baseProps
})
</script>

<template>
  <CmkDialog v-bind="dialogProps" />
</template>
