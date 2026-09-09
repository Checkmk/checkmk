<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import { provideFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import { nextTick, useTemplateRef, watch } from 'vue'

import useInlineEdit, { type InlineEditLeaveReason } from './useInlineEdit'

// A pill toggling between a collapsed read-only summary and inline edit controls, both supplied via the `read-only` and `edit` slots.
const props = withDefaults(
  defineProps<{
    editing?: boolean
    removable?: boolean
    tabFocusable?: boolean
    ariaLabel?: string | undefined
    title?: string | undefined
    editAriaLabel?: string | undefined
    removeLabel?: string | undefined
    /** Veto leaving edit mode; returning `false` keeps the pill open. */
    canLeave?: (reason: InlineEditLeaveReason) => boolean
    /** Attribute marking the edit pane as a focus-navigation scope. */
    scopeMarkerAttr: string
    /** Attribute marking focus-navigation participants within that scope. */
    itemMarkerAttr: string
  }>(),
  {
    editing: false,
    removable: false,
    tabFocusable: true,
    ariaLabel: undefined,
    title: undefined,
    editAriaLabel: undefined,
    removeLabel: undefined,
    canLeave: () => true
  }
)

const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'remove'): void
  (e: 'done', reason: InlineEditLeaveReason): void
}>()

const closedPillRef = useTemplateRef<HTMLElement>('closedPillRef')
const editPaneRef = useTemplateRef<HTMLElement>('editPaneRef')

// Keeps a slotted dropdown's suggestions inside the pane, so the outside-click commit and the Tab
// trap below still count them as part of the pill.
provideFloatingTarget(() => editPaneRef.value ?? undefined)

// Escape returns focus to the collapsed pill; click-outside commits without moving focus.
let returnFocusToClosedPill = false

function onLeave(reason: InlineEditLeaveReason): void {
  if (!props.canLeave(reason)) {
    return
  }
  if (reason === 'escape') {
    returnFocusToClosedPill = true
  }
  emit('done', reason)
}

function onDelete(): void {
  if (props.removable) {
    emit('remove')
  }
}

const { vClickOutside, onOutsideClick, onEscapeCapture, onEscape } = useInlineEdit({
  isOpen: () => props.editing,
  paneRef: editPaneRef,
  onLeave
})

watch(
  () => props.editing,
  (now) => {
    if (!now && returnFocusToClosedPill) {
      returnFocusToClosedPill = false
      void nextTick(() => closedPillRef.value?.focus())
    }
  }
)

defineExpose({
  focus: () => {
    closedPillRef.value?.focus()
  }
})
</script>

<template>
  <span
    class="telemetry-metrics-inline-edit-pill"
    :class="{ 'telemetry-metrics-inline-edit-pill--editing': editing }"
    :aria-label="ariaLabel"
    role="group"
  >
    <span
      v-if="editing"
      ref="editPaneRef"
      v-click-outside="onOutsideClick"
      class="telemetry-metrics-inline-edit-pill__edit"
      :[scopeMarkerAttr]="''"
      :title="title"
      @keydown.tab.capture.stop
      @keydown.esc.capture="onEscapeCapture"
      @keydown.esc.stop="onEscape"
    >
      <slot name="edit" />
      <CmkIconButton
        v-if="removable"
        :[itemMarkerAttr]="''"
        class="telemetry-metrics-inline-edit-pill__remove"
        name="close"
        size="small"
        :title="removeLabel"
        :aria-label="removeLabel"
        @mousedown.prevent
        @click.stop="emit('remove')"
      />
    </span>
    <span
      v-else
      ref="closedPillRef"
      :[itemMarkerAttr]="''"
      class="telemetry-metrics-inline-edit-pill__closed"
      :tabindex="tabFocusable ? 0 : -1"
      @keydown.enter.prevent="emit('edit')"
      @keydown.space.prevent="emit('edit')"
      @keydown.delete.prevent="onDelete"
    >
      <button
        type="button"
        class="telemetry-metrics-inline-edit-pill__main"
        tabindex="-1"
        :title="title"
        :aria-label="editAriaLabel"
        @mousedown.prevent
        @click.stop="emit('edit')"
        @keydown.delete.prevent="onDelete"
      >
        <slot name="read-only" />
      </button>
      <CmkIconButton
        v-if="removable"
        class="telemetry-metrics-inline-edit-pill__remove"
        name="close"
        size="small"
        tabindex="-1"
        :title="removeLabel"
        :aria-label="removeLabel"
        @mousedown.prevent
        @click.stop="emit('remove')"
      />
    </span>
  </span>
</template>

<style scoped>
.telemetry-metrics-inline-edit-pill {
  display: inline-flex;
  align-items: stretch;
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-4);
  white-space: nowrap;
}

.telemetry-metrics-inline-edit-pill:not(.telemetry-metrics-inline-edit-pill--editing):hover {
  background-color: var(--input-hover-bg-color);
}

.telemetry-metrics-inline-edit-pill--editing {
  background: var(--ux-theme-3);
}

.telemetry-metrics-inline-edit-pill__edit,
.telemetry-metrics-inline-edit-pill__closed {
  display: inline-flex;
  align-items: stretch;
  gap: var(--dimension-4);
  padding: 0 var(--dimension-3);
}

.telemetry-metrics-inline-edit-pill__closed:focus-visible {
  outline: revert;
}

.telemetry-metrics-inline-edit-pill__main {
  display: inline-flex;
  gap: var(--dimension-4);
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.telemetry-metrics-inline-edit-pill__main:focus-visible {
  outline: revert;
}

.telemetry-metrics-inline-edit-pill__remove {
  display: inline-flex;
  align-items: center;
}

.telemetry-metrics-inline-edit-pill--editing .telemetry-metrics-inline-edit-pill__remove:hover {
  background-color: var(--default-form-element-bg-color);
}
</style>
