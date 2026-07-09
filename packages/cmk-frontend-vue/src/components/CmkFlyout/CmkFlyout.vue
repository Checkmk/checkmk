<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'

import useId from '@/lib/useId'

import type { FlyoutProps, FlyoutSlots, TriggerAria } from './types'
import { useFlyoutDismiss } from './useFlyoutDismiss'
import { useFlyoutFocus } from './useFlyoutFocus'
import { useFlyoutNesting } from './useFlyoutNesting'

const props = defineProps<FlyoutProps>()

const emit = defineEmits<{
  /** The user dismissed the flyout (Escape, outside press, or focus leaving). The owner reacts by
   * writing `open = false`; `CmkFlyout` never closes itself. */
  (e: 'cancel'): void
}>()

defineSlots<FlyoutSlots>()

const isOpen = (): boolean => props.open

const rootRef = useTemplateRef<HTMLElement>('rootRef')
const popupRef = useTemplateRef<HTMLElement>('popupRef')

const popupId = useId()

const triggerAria = computed<TriggerAria>(() => ({
  'aria-haspopup': 'dialog',
  'aria-expanded': props.open,
  'aria-controls': props.open ? popupId : undefined
}))

const { hasOpenChild } = useFlyoutNesting(isOpen)
const { onFocusOut } = useFlyoutDismiss({
  open: isOpen,
  root: () => rootRef.value,
  hasOpenChild,
  onDismiss: () => emit('cancel')
})
useFlyoutFocus(isOpen, { popup: () => popupRef.value, restoreFocus: () => props.restoreFocus() })

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && props.open && !hasOpenChild()) {
    event.preventDefault()
    emit('cancel')
  }
}
</script>

<template>
  <div
    ref="rootRef"
    class="cmk-flyout"
    :class="{ 'cmk-flyout--open': open }"
    @keydown="onKeydown"
    @focusout="onFocusOut"
  >
    <div class="cmk-flyout__trigger">
      <slot name="trigger" :open="open" :aria="triggerAria" />
    </div>
    <div
      v-if="open"
      :id="popupId"
      ref="popupRef"
      class="cmk-flyout__popup"
      role="dialog"
      :aria-label="label"
      tabindex="-1"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.cmk-flyout {
  position: relative;
  display: inline-block;
}

.cmk-flyout__popup {
  position: absolute;

  /* Overlap the trigger's bottom border so the two borders coincide: no gap, no double border. */
  top: calc(100% - 1px);
  left: 0;
  z-index: var(--z-index-modal-popup);
  display: flex;
  flex-direction: column;
  min-width: max-content;
  background: var(--cmk-flyout-popup-bg, var(--ux-theme-1));
  border: 1px solid var(--cmk-flyout-popup-border-color, var(--default-form-element-border-color));
  border-radius: var(--border-radius);
  color: var(--font-color);
}

/* Square the popup's top-left corner where the trigger meets it. */
.cmk-flyout--open > .cmk-flyout__popup {
  border-top-left-radius: 0;
}

.cmk-flyout--open > .cmk-flyout__trigger {
  position: relative;
  z-index: calc(var(--z-index-modal-popup) + 1);
}
</style>
