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

import CmkButton from '@/components/CmkButton/CmkButton.vue'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

import { MONITORING_SERVICE } from '../MonitoringTableContext'
import FilterCheckboxList from './FilterCheckboxList.vue'
import FilterNumeric from './FilterNumeric.vue'
import FilterStringInput from './FilterStringInput.vue'
import type { ColumnFilterDefinition } from './types'

const FILTER_COMPONENTS: Record<ColumnFilterDefinition['type'], Component> = {
  'checkbox-list': FilterCheckboxList,
  'string-input': FilterStringInput,
  numeric: FilterNumeric
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
const flipLeft = ref(false)
// Swallow the click-outside fired by the same click that opened the popover.
const suppressNextClickOutside = ref(false)

// Staged edits, snapshotted from the committed model on open. Only Apply writes
// this back to the model; cancelling discards it.
const draft = ref<ColumnFilterNode<FilterField> | undefined>(undefined)

// Bumped to force the mounted filter component to re-initialise from the draft.
// The per-type filter components derive their internal display state from the
// model only at setup, so resetting the draft (Clear) needs a remount to take.
const draftKey = ref(0)

const isValid = ref(true)

const panel = ref<HTMLElement | null>(null)
const trigger = ref<HTMLElement | null>(null)

const isActive = computed(() => model.value !== undefined)

const filterComponent = computed(() => FILTER_COMPONENTS[props.definition.type])

function open(): void {
  if (isOpen.value) {
    return
  }
  draft.value = model.value
  isValid.value = true
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
  if (!isValid.value) {
    return
  }
  model.value = draft.value
  close()
}

function cancel(): void {
  close()
}

function clear(): void {
  draft.value = undefined
  isValid.value = true
  draftKey.value += 1
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
  const clipLeft = clippingLeft(triggerEl)
  flipLeft.value = triggerRect.right - clipLeft >= panelEl.offsetWidth
}

function clippingLeft(el: HTMLElement): number {
  let node: HTMLElement | null = el.parentElement
  while (node) {
    const overflowX = getComputedStyle(node).overflowX
    if (overflowX === 'auto' || overflowX === 'scroll' || overflowX === 'hidden') {
      return node.getBoundingClientRect().left
    }
    node = node.parentElement
  }
  return 0
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

// Filter types whose input owns the vertical arrow keys (e.g. a number field's
// native increment/decrement). For these the dropdown must not hijack ArrowUp /
// ArrowDown for row navigation; Tab still moves between rows.
const ARROW_NAV_DISABLED_TYPES = new Set<ColumnFilterDefinition['type']>(['numeric'])

function registerShortcuts(): void {
  if (shortcutIds.length > 0) {
    return
  }
  shortcutIds = [shortcuts.on({ key: ['Escape'] }, close)]
  if (!ARROW_NAV_DISABLED_TYPES.has(props.definition.type)) {
    shortcutIds.push(
      shortcuts.on({ key: ['ArrowDown'], preventDefault: true }, () => moveFocus(1)),
      shortcuts.on({ key: ['ArrowUp'], preventDefault: true }, () => moveFocus(-1))
    )
  }
}

function removeShortcuts(): void {
  if (shortcutIds.length > 0) {
    shortcuts.remove(shortcutIds)
    shortcutIds = []
  }
}

// Closing on Tab-out: only when focus genuinely leaves the panel for another
// element (relatedTarget is null for internal clicks on non-focusable area).
// Focus moving to the trigger is left to the trigger's own click handler, so a
// click on the trigger toggles closed instead of close-then-reopen.
function onFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget as Node | null
  if (next && trigger.value?.contains(next)) {
    return
  }
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
      :class="{
        'monitoring-filter-dropdown__panel--up': flipUp,
        'monitoring-filter-dropdown__panel--left': flipLeft
      }"
      role="group"
      :aria-label="`Filter ${label}`"
      @focusout="onFocusOut"
    >
      <div class="monitoring-filter-dropdown__content">
        <button class="monitoring-filter-dropdown__clear" @click="clear">
          {{ _t('Clear') }}
        </button>

        <hr class="monitoring-filter-dropdown__content-row-separator" />

        <component
          :is="filterComponent"
          :key="draftKey"
          v-model="draft"
          :definition="definition"
          @update:valid="isValid = $event"
        />
      </div>

      <div class="monitoring-filter-dropdown__footer">
        <CmkButton variant="primary" :disabled="!isValid" @click="apply">{{
          _t('Apply')
        }}</CmkButton>
        <CmkButton @click="cancel">{{ _t('Cancel') }}</CmkButton>
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
  box-sizing: border-box;
  width: max-content;
  min-width: 180px;
  max-width: min(90vw, 32rem);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-4);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 25%);
}

.monitoring-filter-dropdown__content {
  width: calc(100% - 2 * var(--dimension-2));
  margin: var(--dimension-2);
}

.monitoring-filter-dropdown__clear {
  border: 0;
  background-color: transparent;
  text-decoration: underline;
  font-weight: var(--font-weight-default);
  padding: 0;
  margin: var(--dimension-3);
  float: right;

  &:hover {
    text-decoration: none;
  }
}

.monitoring-filter-dropdown__content-row-separator {
  width: 100%;
  height: var(--dimension-1);
  border: 0;
  background-color: var(--ux-theme-4);
  margin: var(--dimension-2) 0;
}

.monitoring-filter-dropdown__panel--up {
  top: auto;
  bottom: 100%;
  margin-top: 0;
  margin-bottom: var(--dimension-2);
}

.monitoring-filter-dropdown__panel--left {
  left: auto;
  right: 0;
}

.monitoring-filter-dropdown__footer {
  display: flex;
  gap: var(--dimension-4);
  justify-content: flex-end;
  margin-top: var(--dimension-2);
  padding: var(--dimension-4) var(--dimension-3);
  border-top: 1px solid var(--ux-theme-4);
  align-items: center;
}
</style>
