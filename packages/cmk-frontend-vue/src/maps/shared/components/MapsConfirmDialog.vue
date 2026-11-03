<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A question before an action that cannot be taken back, laid out like Checkmk's
newer confirm dialogs (e.g. the graph designer's delete confirmation): title and
text left-aligned, the action first. The icon stays at a size its 48px bitmap
can fill; CmkPopupDialog would blow it up to 77px.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon, { type SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import CmkPopup from 'cmk-ui-library/components/CmkPopup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { DialogTitle } from 'reka-ui'
import { computed } from 'vue'

type DialogVariant = 'error' | 'warning' | 'success' | 'info'

const VARIANT_ICON = {
  error: 'error',
  warning: 'warning',
  success: 'checkmark',
  info: 'info-circle'
} as const satisfies Record<DialogVariant, SimpleIcons>

// The confirm button colour follows the variant, the way CmkAlert derives it
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
  <CmkPopup :open="open" @close="emit('cancel')">
    <div class="maps-confirm-dialog">
      <div class="maps-confirm-dialog__header">
        <CmkIcon :name="VARIANT_ICON[variant]" size="xxlarge" />
        <DialogTitle as-child>
          <CmkHeading type="h2">{{ title }}</CmkHeading>
        </DialogTitle>
      </div>
      <CmkParagraph v-if="message" class="maps-confirm-dialog__message">{{ message }}</CmkParagraph>
      <slot />
      <div class="maps-confirm-dialog__actions">
        <CmkButton :variant="VARIANT_BUTTON[variant]" :disabled="busy" @click="emit('confirm')">
          {{ confirmTitle }}
        </CmkButton>
        <CmkButton variant="secondary" @click="emit('cancel')">{{ cancelTitle }}</CmkButton>
      </div>
    </div>
  </CmkPopup>
</template>

<style scoped>
.maps-confirm-dialog {
  display: flex;
  flex-direction: column;
  align-self: stretch;
  gap: var(--dimension-6);
  max-width: 60ch;
}

.maps-confirm-dialog__header {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
}

.maps-confirm-dialog__message {
  margin: 0;
}

.maps-confirm-dialog__actions {
  display: flex;
  gap: var(--dimension-4);
}
</style>
