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
communicates via v-model (a `ColumnFilterValue` or undefined). New filter types
(numeric range, IP range, ...) register in FILTER_COMPONENTS without touching
this shell.

Edits are staged in a `draft` that is snapshotted from the committed model when
the popover opens. The mounted filter component binds to that draft, so toggling
options never touches the committed model directly. Only "Apply" commits the
draft (closing the popover and updating the table); "Cancel", Escape and
click-outside discard the draft, leaving the model at the state it had on open.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { provideFloatingTarget } from 'cmk-ui-library/lib/useFloatingTarget'
import useId from 'cmk-ui-library/lib/useId'
import {
  type CSSProperties,
  type Component,
  computed,
  inject,
  nextTick,
  onBeforeUnmount,
  ref
} from 'vue'

import type { FilterField } from '@/monitoring/shared/api/types'

import { MONITORING_SERVICE } from '../MonitoringTableContext'
import FilterAutocompleteChoice from './FilterAutocompleteChoice.vue'
import FilterBooleanGroup from './FilterBooleanGroup.vue'
import FilterCheckboxList from './FilterCheckboxList.vue'
import FilterCheckboxListWithFlags from './FilterCheckboxListWithFlags.vue'
import FilterColumnVisibility from './FilterColumnVisibility.vue'
import FilterDateTimeRange from './FilterDateTimeRange.vue'
import FilterNumeric from './FilterNumeric.vue'
import FilterStringInput from './FilterStringInput.vue'
import FilterVisualFilter from './FilterVisualFilter.vue'
import type { ColumnFilterDefinition, ColumnFilterValue, SortDirection } from './types'

const FILTER_COMPONENTS: Record<ColumnFilterDefinition['type'], Component> = {
  'checkbox-list': FilterCheckboxList,
  'checkbox-list-with-flags': FilterCheckboxListWithFlags,
  'string-input': FilterStringInput,
  numeric: FilterNumeric,
  'date-time-range': FilterDateTimeRange,
  'boolean-group': FilterBooleanGroup,
  'autocomplete-choice': FilterAutocompleteChoice,
  'column-visibility': FilterColumnVisibility,
  'visual-filter': FilterVisualFilter
}

const props = defineProps<{
  definition: ColumnFilterDefinition
  /** Human-readable column name, used for the accessible popover label. */
  label: string
  clearLabel?: string
  /** Title of the filter section, shown opposite the clear button. */
  heading?: string
  /**
   * Selector of the ancestor the panel lines up with, resolved with `closest`.
   * Unset, the panel lines up with the trigger itself.
   */
  anchor?: string
  /** Offer the column's sort directions above the filter. */
  sortable?: boolean
}>()

const model = defineModel<ColumnFilterValue<FilterField> | undefined>({ default: undefined })

const sort = defineModel<SortDirection>('sort', { default: false })

const { _t } = usei18n()
const panelId = useId()

const vClickOutside = useClickOutside()
const shortcuts = getKeyShortcutServiceInstance()
let shortcutIds: string[] = []

const monitoringService = inject(MONITORING_SERVICE, null)

const isOpen = ref(false)
const flipUp = ref(false)
const alignment = ref<CSSProperties>({})
// Swallow the click-outside fired by the same click that opened the popover.
const suppressNextClickOutside = ref(false)
// Whether the press behind the current click started within the funnel.
const pressStartedInside = ref(false)

// Staged edits, snapshotted from the committed model on open. Only Apply writes
// this back to the model; cancelling discards it.
const draft = ref<ColumnFilterValue<FilterField> | undefined>(undefined)

// Bumped to force the mounted filter component to re-initialise from the draft.
// The per-type filter components derive their internal display state from the
// model only at setup, so resetting the draft (Clear) needs a remount to take.
const draftKey = ref(0)

const isValid = ref(true)

const panel = ref<HTMLElement | null>(null)
const trigger = ref<HTMLElement | null>(null)

// A filter component may mount floating content of its own (a CmkDropdown's
// suggestion list, say). Unless it lands inside the panel it teleports to the
// body, and then opening it reads as a click outside the panel and closes the
// whole funnel. Registering the panel as the floating target keeps that content
// within it, the way CmkSlideIn does for its own descendants.
provideFloatingTarget(() => panel.value ?? undefined)

const isActive = computed(() => model.value !== undefined)

const sortOptions = computed<{ direction: SortDirection; label: string }[]>(() => [
  { direction: 'asc', label: _t('Sort ascending') },
  { direction: 'desc', label: _t('Sort descending') },
  { direction: false, label: _t('No sorting / default sorting') }
])

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
  // Capture, so it still runs when the floating content stops propagation.
  document.addEventListener('pointerdown', onPointerDown, true)
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
  document.removeEventListener('pointerdown', onPointerDown, true)
  pressStartedInside.value = false
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

// Floating content inside the panel typically unmounts on the very click that
// activates it - picking a dropdown option, say. The click-outside check runs
// after that, on a target already detached from the document, so it no longer
// tests as "inside" and the funnel would close along with it. Pointerdown fires
// while the target is still mounted, so that is where "inside" is decided.
function onPointerDown(event: PointerEvent): void {
  const target = event.target as Node | null
  pressStartedInside.value =
    target !== null &&
    (panel.value?.contains(target) === true || trigger.value?.contains(target) === true)
}

function onClickOutside(): void {
  if (suppressNextClickOutside.value || pressStartedInside.value) {
    return
  }
  close()
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

  const anchorRect = anchorElement(triggerEl).getBoundingClientRect()
  const clipping = clippingBounds(triggerEl)
  const alignLeft = Math.max(anchorRect.left, clipping.left)
  const alignRight = Math.min(anchorRect.right, clipping.right)
  const overflowsRight = alignLeft + panelEl.offsetWidth > clipping.right
  const fitsLeftwards = alignRight - clipping.left >= panelEl.offsetWidth
  alignment.value =
    overflowsRight && fitsLeftwards
      ? { left: 'auto', right: `${triggerRect.right - alignRight}px` }
      : { left: `${alignLeft - triggerRect.left}px`, right: 'auto' }
}

function anchorElement(el: HTMLElement): HTMLElement {
  return props.anchor === undefined ? el : (el.closest<HTMLElement>(props.anchor) ?? el)
}

function clippingBounds(el: HTMLElement): { left: number; right: number } {
  let node: HTMLElement | null = el.parentElement
  while (node) {
    const overflowX = getComputedStyle(node).overflowX
    if (overflowX === 'auto' || overflowX === 'scroll' || overflowX === 'hidden') {
      const rect = node.getBoundingClientRect()
      return { left: rect.left, right: rect.right }
    }
    node = node.parentElement
  }
  return { left: 0, right: window.innerWidth }
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

// Filter types whose input owns the vertical arrow keys. Numeric/date-time
// fields use them for native increment/decrement; boolean-group and
// checkbox-list-with-flags render a tri-state radio group, and reka-ui already
// gives each one its own roving-tabindex Up/Down handling. For all of these
// the dropdown must not hijack ArrowUp/ArrowDown for row navigation - Tab
// still moves between rows, including into and out of a radio group.
const ARROW_NAV_DISABLED_TYPES = new Set<ColumnFilterDefinition['type']>([
  'numeric',
  'date-time-range',
  'boolean-group',
  'checkbox-list-with-flags'
])

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
  document.removeEventListener('pointerdown', onPointerDown, true)
})
</script>

<template>
  <span ref="trigger" class="monitoring-filter-dropdown">
    <slot
      name="trigger"
      :toggle="toggle"
      :is-open="isOpen"
      :is-active="isActive"
      :panel-id="panelId"
    />

    <div
      v-if="isOpen"
      :id="panelId"
      ref="panel"
      v-click-outside="onClickOutside"
      class="monitoring-filter-dropdown__panel"
      :class="{ 'monitoring-filter-dropdown__panel--up': flipUp }"
      :style="alignment"
      role="group"
      :aria-label="`Filter ${label}`"
      @focusout="onFocusOut"
    >
      <div v-if="sortable" class="monitoring-filter-dropdown__sort">
        <button
          v-for="option in sortOptions"
          :key="String(option.direction)"
          type="button"
          class="monitoring-filter-dropdown__sort-option"
          :aria-pressed="sort === option.direction"
          @click="sort = option.direction"
        >
          <CmkMultitoneIcon
            v-if="option.direction !== false"
            name="dashlet-resize"
            :rotate="option.direction === 'asc' ? 180 : 0"
            primary-color="font"
            aria-hidden="true"
            size="xsmall"
          />
          <span
            v-else
            class="monitoring-filter-dropdown__sort-option-spacer"
            aria-hidden="true"
          ></span>
          {{ option.label }}
          <span
            v-if="sort === option.direction"
            class="monitoring-filter-dropdown__sort-marker"
            aria-hidden="true"
          ></span>
        </button>
      </div>

      <div class="monitoring-filter-dropdown__content">
        <div class="monitoring-filter-dropdown__content-header">
          <span v-if="heading" class="monitoring-filter-dropdown__heading">{{ heading }}</span>
          <CmkButton
            variant="text"
            size="small"
            class="monitoring-filter-dropdown__clear"
            @click="clear"
          >
            {{ props.clearLabel ?? _t('Clear') }}
          </CmkButton>
        </div>

        <component
          :is="filterComponent"
          :key="draftKey"
          v-model="draft"
          :definition="definition"
          @update:valid="isValid = $event"
        />
      </div>

      <div class="monitoring-filter-dropdown__footer">
        <CmkButton variant="primary" size="small" :disabled="!isValid" @click="apply">{{
          _t('Apply')
        }}</CmkButton>
        <CmkButton size="small" @click="cancel">{{ _t('Cancel') }}</CmkButton>
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
  min-width: 330px;
  max-width: min(90vw, 32rem);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-4);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 25%);
  font-weight: var(--font-weight-default);
}

.monitoring-filter-dropdown__sort {
  display: flex;
  flex-direction: column;
  padding: var(--dimension-3) 0;
  border-bottom: 1px solid var(--ux-theme-4);
}

.monitoring-filter-dropdown__sort-option {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  padding: var(--dimension-3) var(--dimension-5);
  background: transparent;
  border: none;
  margin: 0;
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: 0;
  line-height: 20px;

  &:hover {
    background-color: var(--ux-theme-3);
  }
}

.monitoring-filter-dropdown__sort-option-spacer {
  width: 10px;
}

.monitoring-filter-dropdown__sort-marker {
  width: var(--dimension-3);
  height: var(--dimension-3);
  margin-left: auto;
  border-radius: 50%;
  background: var(--success);
}

.monitoring-filter-dropdown__content {
  width: 100%;
}

.monitoring-filter-dropdown__content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
}

.monitoring-filter-dropdown__heading {
  font-weight: var(--font-weight-bold);
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
  justify-content: flex-end;
  padding: var(--dimension-4) var(--dimension-5);
  align-items: center;
  border-top: 1px solid var(--ux-theme-4);
}
</style>
