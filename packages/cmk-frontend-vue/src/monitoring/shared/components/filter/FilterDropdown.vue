<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Generic popover shell for a column filter. It owns only shell concerns:
open/close, positioning, click-outside and keyboard navigation between the
focusable rows (via the shared KeyShortcutService). The actual filter UI is
mounted from a per-type registry; each filter component owns its own state and
communicates via v-model (a `ColumnFilterNode` or undefined). New filter types
(numeric range, IP range, ...) register in FILTER_COMPONENTS without touching
this shell.

Edits are staged in a `draft` that is snapshotted from the committed model when
the popover opens. The mounted filter component binds to that draft, so toggling
options never touches the committed model directly. Only "Apply" commits the
draft (closing the popover and updating the table); "Cancel", Escape and
click-outside discard the draft, leaving the model at the state it had on open.
-->
<script setup lang="ts">
import { type Component, computed, inject, nextTick, onBeforeUnmount, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { getKeyShortcutServiceInstance } from '@/lib/keyShortcuts'
import useClickOutside from '@/lib/useClickOutside'

import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import { MONITORING_SERVICE } from '../MonitoringTableContext'
import FilterCheckboxList from './FilterCheckboxList.vue'
import type { ColumnFilterDefinition } from './types'

const FILTER_COMPONENTS: Record<ColumnFilterDefinition['type'], Component> = {
  'checkbox-list': FilterCheckboxList
}

const props = defineProps<{
  definition: ColumnFilterDefinition
  /** Human-readable column name, used for the accessible popover label. */
  label: string
}>()

const model = defineModel<ColumnFilterNode<FilterField> | undefined>({ default: undefined })

const { _t } = usei18n()

const vClickOutside = useClickOutside()
const shortcuts = getKeyShortcutServiceInstance()
let shortcutIds: string[] = []

const monitoringService = inject(MONITORING_SERVICE, null)

const isOpen = ref(false)
const flipUp = ref(false)
// Swallow the click-outside fired by the same click that opened the popover.
const suppressNextClickOutside = ref(false)

// Staged edits, snapshotted from the committed model on open. Only Apply writes
// this back to the model; cancelling discards it.
const draft = ref<ColumnFilterNode<FilterField> | undefined>(undefined)

const panel = ref<HTMLElement | null>(null)
const trigger = ref<HTMLElement | null>(null)

const isActive = computed(() => model.value !== undefined)

const filterComponent = computed(() => FILTER_COMPONENTS[props.definition.type])

function open(): void {
  if (isOpen.value) {
    return
  }
  draft.value = model.value
  isOpen.value = true
  monitoringService?.beginAutoPause()
  suppressNextClickOutside.value = true
  setTimeout(() => {
    suppressNextClickOutside.value = false
  }, 0)
  registerShortcuts()
  void nextTick(() => {
    positionPanel()
    focusRow(0)
  })
}

function close(): void {
  if (!isOpen.value) {
    return
  }
  isOpen.value = false
  monitoringService?.endAutoPause()
  removeShortcuts()
  trigger.value?.querySelector('button')?.focus()
}

function toggle(): void {
  if (isOpen.value) {
    close()
  } else {
    open()
  }
}

function apply(): void {
  model.value = draft.value
  close()
}

function cancel(): void {
  close()
}

function onClickOutside(): void {
  if (!suppressNextClickOutside.value) {
    close()
  }
}

function positionPanel(): void {
  const panelEl = panel.value
  const triggerEl = trigger.value
  if (!panelEl || !triggerEl) {
    return
  }
  const triggerRect = triggerEl.getBoundingClientRect()
  const spaceBelow = window.innerHeight - triggerRect.bottom
  flipUp.value = spaceBelow < panelEl.offsetHeight && triggerRect.top > spaceBelow
}

// The focusable rows are whatever the mounted filter component renders (search
// field, checkbox buttons, ...). Querying them keeps navigation type-agnostic.
function focusables(): HTMLElement[] {
  if (!panel.value) {
    return []
  }
  return Array.from(panel.value.querySelectorAll<HTMLElement>('input, button'))
}

function focusRow(index: number): void {
  const items = focusables()
  if (items.length === 0) {
    return
  }
  const clamped = Math.min(items.length - 1, Math.max(0, index))
  items[clamped]?.focus()
}

function moveFocus(delta: number): void {
  const items = focusables()
  if (items.length === 0) {
    return
  }
  const current = items.indexOf(document.activeElement as HTMLElement)
  if (current < 0) {
    focusRow(delta > 0 ? 0 : items.length - 1)
    return
  }
  focusRow(current + delta)
}

function registerShortcuts(): void {
  if (shortcutIds.length > 0) {
    return
  }
  shortcutIds = [
    shortcuts.on({ key: ['ArrowDown'], preventDefault: true }, () => moveFocus(1)),
    shortcuts.on({ key: ['ArrowUp'], preventDefault: true }, () => moveFocus(-1)),
    shortcuts.on({ key: ['Escape'] }, close)
  ]
}

function removeShortcuts(): void {
  if (shortcutIds.length > 0) {
    shortcuts.remove(shortcutIds)
    shortcutIds = []
  }
}

// Closing on Tab-out: only when focus genuinely leaves the panel for another
// element (relatedTarget is null for internal clicks on non-focusable area).
function onFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget as Node | null
  if (next && panel.value && !panel.value.contains(next)) {
    close()
  }
}

onBeforeUnmount(() => {
  if (isOpen.value) {
    monitoringService?.endAutoPause()
  }
  removeShortcuts()
})
</script>

<template>
  <span ref="trigger" class="monitoring-filter-dropdown">
    <slot name="trigger" :toggle="toggle" :is-open="isOpen" :is-active="isActive" />

    <div
      v-if="isOpen"
      ref="panel"
      v-click-outside="onClickOutside"
      class="monitoring-filter-dropdown__panel"
      :class="{ 'monitoring-filter-dropdown__panel--up': flipUp }"
      role="group"
      :aria-label="`Filter ${label}`"
      @focusout="onFocusOut"
    >
      <component :is="filterComponent" v-model="draft" :definition="definition" />

      <div class="monitoring-filter-dropdown__footer">
        <CmkInlineButton icon="checkmark" @click="apply">{{ _t('Apply') }}</CmkInlineButton>
        <CmkInlineButton icon="cancel" @click="cancel">{{ _t('Cancel') }}</CmkInlineButton>
      </div>
    </div>
  </span>
</template>

<style scoped>
.monitoring-filter-dropdown {
  position: relative;
  display: inline-flex;
  height: 100%;
}

.monitoring-filter-dropdown__panel {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: var(--z-index-dropdown-offset, 100);
  min-width: 180px;
  max-width: 320px;
  margin-top: var(--dimension-2);
  padding: var(--dimension-2);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-4);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 25%);
}

.monitoring-filter-dropdown__panel--up {
  top: auto;
  bottom: 100%;
  margin-top: 0;
  margin-bottom: var(--dimension-2);
}

.monitoring-filter-dropdown__footer {
  display: flex;
  gap: var(--dimension-4);
  justify-content: space-around;
  margin-top: var(--dimension-4);
  padding: var(--dimension-3) 0 var(--dimension-2);
  border-top: 1px solid var(--ux-theme-4);
  align-items: center;
}
</style>
