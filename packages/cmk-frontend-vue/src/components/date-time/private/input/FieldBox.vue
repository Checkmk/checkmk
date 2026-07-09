<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { TriggerAria } from '@/components/CmkFlyout'
import { type CmkMultitoneIconNames } from '@/components/CmkIcon'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

const props = defineProps<{
  /** Optional leading CmkMultitoneIcon name. */
  icon?: CmkMultitoneIconNames | undefined
  /** Dim the box and show the not-allowed cursor across the whole field. */
  disabled?: boolean
  /** Square the bottom into a popup opening directly below. */
  open?: boolean
  /** Act as the flyout trigger (icon button + click to open). See the component comment. */
  asTrigger?: boolean
  /** ARIA wiring from the flyout (haspopup/expanded/controls); placed on the icon trigger button. */
  triggerAria?: TriggerAria | undefined
  /** Accessible name for the trigger button (e.g. "Open calendar"). */
  iconLabel?: TranslatedString | undefined
}>()

const emit = defineEmits<{
  /** Open the popup (no-op if already open): clicking into the field. */
  (e: 'open'): void
  /** Toggle the popup open/closed: the icon trigger button. */
  (e: 'toggle'): void
}>()

defineSlots<{
  /** The segmented field(s) wrapped by the box chrome. */
  default?: () => unknown
}>()

const triggerButtonRef = useTemplateRef<HTMLButtonElement>('triggerButtonRef')

function onBoxClick(): void {
  if (props.asTrigger && !props.disabled) {
    emit('open')
  }
}

/** Focus the icon trigger button (the control owning the popup aria). No-op unless an icon trigger
 *  button is rendered (i.e. `asTrigger && icon`). */
defineExpose({ focusTriggerButton: () => triggerButtonRef.value?.focus() })
</script>

<template>
  <span
    class="cmk-field-box"
    :class="{ 'cmk-field-box--disabled': disabled, 'cmk-field-box--open': open }"
    @click="onBoxClick"
  >
    <button
      v-if="asTrigger && icon"
      ref="triggerButtonRef"
      type="button"
      class="cmk-field-box__trigger"
      :aria-label="iconLabel"
      :disabled="disabled"
      v-bind="triggerAria"
      @click.stop="emit('toggle')"
    >
      <CmkMultitoneIcon :name="icon" primary-color="font" size="small" aria-hidden="true" />
    </button>
    <CmkMultitoneIcon
      v-else-if="icon"
      :name="icon"
      primary-color="font"
      size="small"
      aria-hidden="true"
    />
    <slot />
  </span>
</template>

<style scoped>
.cmk-field-box {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  height: var(--form-field-height);
  padding: 0 var(--dimension-3);
  border: 1px solid var(--color-mid-grey-50);
  border-radius: var(--dimension-3);
  background: var(--default-form-element-bg-color);
  cursor: text;
}

body[data-theme='modern-dark'] .cmk-field-box {
  border-color: var(--color-mid-grey-60);
}

.cmk-field-box--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* Square the bottom into the popup opening below: drop the bottom border and corners. */
.cmk-field-box--open {
  border-bottom-color: transparent;
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.cmk-field-box__trigger {
  display: inline-flex;
  align-items: center;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.cmk-field-box__trigger:focus-visible {
  outline: revert;
}

.cmk-field-box--disabled .cmk-field-box__trigger {
  pointer-events: none;
}
</style>
