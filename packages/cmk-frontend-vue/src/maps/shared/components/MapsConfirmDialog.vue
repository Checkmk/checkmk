<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkPopupDialog from 'cmk-ui-library/components/CmkPopupDialog.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

type DialogVariant = 'error' | 'warning' | 'success' | 'info'

const VARIANT_ICON = {
  error: 'error',
  warning: 'warning',
  success: 'checkmark',
  info: 'info-circle'
} as const satisfies Record<DialogVariant, SimpleIcons>

// The confirm button colour follows the variant, the way CmkAlertBox derives it
// from its own, so the caller needs no separate prop.
const VARIANT_BUTTON = {
  error: 'danger',
  warning: 'warning',
  success: 'success',
  info: 'info'
} as const

const props = withDefaults(
  defineProps<{
    open: boolean
    title: TranslatedString
    message?: TranslatedString
    confirmLabel?: TranslatedString
    cancelLabel?: TranslatedString
    variant?: DialogVariant
    /** Keeps the confirm button unclickable while the action is running. */
    busy?: boolean
  }>(),
  {
    message: untranslated(''),
    confirmLabel: untranslated(''),
    cancelLabel: untranslated(''),
    variant: 'warning'
  }
)

const emit = defineEmits<{ confirm: []; cancel: [] }>()
const { _t } = usei18n()

const confirmTitle = computed(() => (props.confirmLabel ? props.confirmLabel : _t('Confirm')))
const cancelTitle = computed(() => (props.cancelLabel ? props.cancelLabel : _t('Cancel')))
</script>

<template>
  <CmkPopupDialog :open="open" :icon="VARIANT_ICON[variant]" :title="title" @close="emit('cancel')">
    <CmkParagraph v-if="message" class="maps-confirm-dialog__message">{{ message }}</CmkParagraph>
    <slot />
    <div class="maps-confirm-dialog__actions">
      <CmkButton variant="optional" @click="emit('cancel')">{{ cancelTitle }}</CmkButton>
      <CmkButton :variant="VARIANT_BUTTON[variant]" :disabled="busy" @click="emit('confirm')">
        {{ confirmTitle }}
      </CmkButton>
    </div>
  </CmkPopupDialog>
</template>

<style scoped>
.maps-confirm-dialog__message {
  max-width: 46ch;
  margin-bottom: var(--dimension-6);
  text-align: center;
}

.maps-confirm-dialog__actions {
  display: flex;
  justify-content: center;
  gap: var(--dimension-3);
}
</style>
