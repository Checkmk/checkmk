<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkPopup from 'cmk-ui-library/components/CmkPopup.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { DialogTitle } from 'reka-ui'
import { onUnmounted, useTemplateRef, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: TranslatedString
    closable?: boolean
  }>(),
  { closable: true, title: untranslated('') }
)

defineEmits<{ close: [] }>()

const { _t } = usei18n()

// CmkPopup only moves focus in when ``open`` flips, and these modals are
// mounted already open -- so focus would stay on whatever opened them, and
// Escape would reach that surface too.
const shell = useTemplateRef<HTMLElement>('shell')
let lastFocused: HTMLElement | null = null

function restoreFocus(): void {
  if (lastFocused?.isConnected) {
    lastFocused.focus()
  }
  lastFocused = null
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
    } else {
      restoreFocus()
    }
  },
  { immediate: true, flush: 'post' }
)
// The dialog's content is portalled in after this component mounts.
watch(shell, (el) => el?.closest<HTMLElement>('[role="dialog"]')?.focus())

// Only once the dialog is gone: while it stands, its focus trap pulls focus back.
onUnmounted(restoreFocus)
</script>

<template>
  <CmkPopup :open="open" @close="$emit('close')">
    <div ref="shell" class="maps-modal__shell">
      <header v-if="$slots.header || title" class="maps-modal__header">
        <DialogTitle as-child>
          <CmkHeading type="h3" class="maps-modal__title">
            <slot name="header">{{ title }}</slot>
          </CmkHeading>
        </DialogTitle>
        <CmkIconButton
          v-if="closable"
          name="close"
          size="small"
          :title="_t('Close')"
          :aria-label="_t('Close')"
          @click="$emit('close')"
        />
      </header>
      <div class="maps-modal__body">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="maps-modal__footer">
        <slot name="footer" />
      </footer>
    </div>
  </CmkPopup>
</template>

<style scoped>
/* CmkPopup's container already is the dialog surface — it carries the
   background and the padding. The shell only lays the three regions out inside
   it; painting a second surface here would show up as a frame around it. */
.maps-modal__shell {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.maps-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding-bottom: var(--dimension-5);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-modal__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-modal__body {
  padding: var(--dimension-6) 0;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.maps-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-3);
  padding-top: var(--dimension-5);
  border-top: 1px solid var(--default-border-color);
}
</style>
