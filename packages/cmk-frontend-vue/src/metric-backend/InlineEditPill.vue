<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { nextTick, useTemplateRef, watch } from 'vue'

import CmkIconButton from '@/components/CmkIconButton.vue'

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
    class="metric-backend-inline-edit-pill"
    :class="{ 'metric-backend-inline-edit-pill--editing': editing }"
    :aria-label="ariaLabel"
    role="group"
  >
    <span
      v-if="editing"
      ref="editPaneRef"
      v-click-outside="onOutsideClick"
      class="metric-backend-inline-edit-pill__edit"
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
        class="metric-backend-inline-edit-pill__remove"
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
      class="metric-backend-inline-edit-pill__closed"
      :tabindex="tabFocusable ? 0 : -1"
      @keydown.enter.prevent="emit('edit')"
      @keydown.space.prevent="emit('edit')"
      @keydown.delete.prevent="emit('remove')"
    >
      <button
        type="button"
        class="metric-backend-inline-edit-pill__main"
        tabindex="-1"
        :title="title"
        :aria-label="editAriaLabel"
        @mousedown.prevent
        @click.stop="emit('edit')"
        @keydown.delete.prevent="emit('remove')"
      >
        <slot name="read-only" />
      </button>
      <CmkIconButton
        v-if="removable"
        class="metric-backend-inline-edit-pill__remove"
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
.metric-backend-inline-edit-pill {
  display: inline-flex;
  align-items: stretch;
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-4);
  padding-right: var(--dimension-3);
  white-space: nowrap;
}

.metric-backend-inline-edit-pill:not(.metric-backend-inline-edit-pill--editing):hover {
  background-color: var(--input-hover-bg-color);
}

.metric-backend-inline-edit-pill--editing {
  background: var(--ux-theme-3);
}

.metric-backend-inline-edit-pill__edit {
  display: inline-flex;
}

.metric-backend-inline-edit-pill__closed {
  display: inline-flex;
  align-items: stretch;
}

.metric-backend-inline-edit-pill__closed:focus-visible {
  outline: revert;
}

.metric-backend-inline-edit-pill__main {
  display: inline-flex;
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.metric-backend-inline-edit-pill__main:focus-visible {
  outline: revert;
}

.metric-backend-inline-edit-pill__remove {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--dimension-2);
}

.metric-backend-inline-edit-pill--editing .metric-backend-inline-edit-pill__remove:hover {
  background-color: var(--default-form-element-bg-color);
}
</style>
