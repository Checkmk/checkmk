<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkFlyout, { type FlyoutSlots } from '@/components/CmkFlyout'

import type { DateTimeSaveSlots } from '../../types'
import DateTimeFlyoutFooter from './DateTimeFlyoutFooter.vue'

const props = withDefaults(
  defineProps<{
    /** Renders the save slot behind a checkbox in the footer. */
    saveMode?: boolean
    /** Blocks cancellation while saving is in progress. */
    pendingSave?: boolean
    /** Label for the save checkbox. */
    saveLabel?: TranslatedString
    /** Show the Apply/Cancel footer even when not in save mode. */
    showActions?: boolean
    /** Disable the Apply action. */
    applyDisabled?: boolean
    /** Reason the Apply action is disabled. */
    applyDisabledReason?: TranslatedString | undefined
    /** Stretch the Apply/Cancel buttons across the footer. */
    stretchActions?: boolean
    /** Accessible name for the popup dialog (sets `aria-label`). */
    label?: TranslatedString
    /** Popup fill: the calendar-based pickers use the `gradient`; the Time picker opts into `solid`. */
    popupBackground?: 'gradient' | 'solid'
    /** Border tone for the popup, footer, and trigger. */
    popupBorder?: 'container' | 'field'
    /** Restore focus to the trigger when the popup closes with focus inside it (see `CmkFlyout`). */
    restoreFocus: () => void
  }>(),
  {
    saveMode: false,
    pendingSave: false,
    showActions: false,
    applyDisabled: false,
    stretchActions: false,
    popupBackground: 'gradient',
    popupBorder: 'field'
  }
)

/** Whether the popup is open. Two-way bound; the owner can open/close it programmatically. */
const open = defineModel<boolean>('open', { required: true })
/** Whether the footer's Save checkbox is ticked (only meaningful in save mode). */
const saveChecked = defineModel<boolean>('saveChecked', { default: false })

const emit = defineEmits<{
  /** The user pressed the footer's Apply button. The owner's handler owns the save handler, the
   *  model commit, and closing the flyout (see `useDateTimeDraft`'s `confirm`). */
  (e: 'apply'): void
  /** The flyout was dismissed without applying (footer Cancel, or `CmkFlyout`'s own dismissal). */
  (e: 'cancel'): void
}>()

defineSlots<FlyoutSlots & DateTimeSaveSlots>()

function onCancel(): void {
  if (props.pendingSave) {
    return
  }
  open.value = false
  emit('cancel')
}
</script>

<template>
  <CmkFlyout
    :open="open"
    :class="[
      `cmk-date-time-flyout--${popupBackground}`,
      `cmk-date-time-flyout--border-${popupBorder}`
    ]"
    :label="label"
    :restore-focus="restoreFocus"
    @cancel="onCancel"
  >
    <template #trigger="{ open: isOpen, aria }">
      <slot name="trigger" :open="isOpen" :aria="aria" />
    </template>

    <slot />

    <DateTimeFlyoutFooter
      v-if="saveMode || showActions"
      v-model:save-checked="saveChecked"
      :save-mode="saveMode"
      :save-label="saveLabel"
      :apply-disabled="applyDisabled"
      :apply-disabled-reason="applyDisabledReason"
      :pending-save="pendingSave"
      :stretch-actions="stretchActions"
      @apply="emit('apply')"
      @cancel="onCancel"
    >
      <template #save><slot name="save" /></template>
    </DateTimeFlyoutFooter>
  </CmkFlyout>
</template>

<style scoped>
.cmk-date-time-flyout--gradient {
  --cmk-flyout-popup-bg: linear-gradient(to bottom, var(--ux-theme-1), var(--ux-theme-4));
}

.cmk-date-time-flyout--solid {
  --cmk-flyout-popup-bg: var(--ux-theme-4);
}

.cmk-date-time-flyout--border-container {
  --cmk-flyout-popup-border-color: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .cmk-date-time-flyout--border-container {
  --cmk-flyout-popup-border-color: var(--color-mid-grey-90);
}

.cmk-date-time-flyout--border-field {
  --cmk-flyout-popup-border-color: var(--color-mid-grey-50);
}

body[data-theme='modern-dark'] .cmk-date-time-flyout--border-field {
  --cmk-flyout-popup-border-color: var(--color-mid-grey-60);
}
</style>
