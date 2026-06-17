<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="M extends 'single' | 'range'">
import { CalendarDate, today } from '@internationalized/date'
import { computed, shallowRef, useTemplateRef, watch } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'

import type { ResolvedDateTimeSettings } from '../../types'
import CalendarControls from './CalendarControls.vue'
import CalendarGrid from './CalendarGrid.vue'
import type { CalendarMode, CalendarSelection } from './types'
import { defaultYearRange, monthFromIndex, monthIndex } from './util'

/** The selection type implied by `mode`: a single date in `single`, the two-endpoint span in `range`. */
type SelectionFor<Mode extends CalendarMode> = Mode extends 'single'
  ? CalendarDate | null
  : CalendarSelection

const props = withDefaults(
  defineProps<{
    /** Number of month grids shown side by side. Default 1. */
    grids?: number
    /** Single date or date range selection. */
    mode: M
    /** Resolved locale settings; read here for the dropdown/timezone and forwarded to each
     *  {@link CalendarGrid}. */
    settings: ResolvedDateTimeSettings
    /** `[from, to]` span for the year dropdowns. Defaults to {@link defaultYearRange}. */
    yearRange?: [number, number]
  }>(),
  {
    grids: 1
  }
)

const effectiveYearRange = computed<[number, number]>(() => props.yearRange ?? defaultYearRange())

/** `single`: `CalendarDate | null`. `range`: `CalendarSelection`. */
const selection = defineModel<SelectionFor<M>>('selection', {
  required: true
})

defineSlots<{
  /** Content rendered beside the month grids (e.g. the range picker's quick-range presets). */
  aside?: () => unknown
}>()

// --- visible-month window -------------------------------------------------------
/** Month shown by the first grid (day is always 1). */
const firstVisibleMonth = shallowRef<CalendarDate>(
  monthFromIndex(monthIndex(today(props.settings.timeZone)))
)
const visibleMonths = computed<CalendarDate[]>(() =>
  Array.from({ length: props.grids }, (_unused, i) => firstVisibleMonth.value.add({ months: i }))
)
const focusedDate = shallowRef<CalendarDate | null>(null)
const hoverDate = shallowRef<CalendarDate | null>(null)

// --- selection projection -------------------------------------------------------
const singleValue = computed<CalendarDate | null>(() =>
  selection.value instanceof CalendarDate ? selection.value : null
)
const rangeValue = computed<CalendarSelection>(() => {
  const value = selection.value
  if (value && typeof value === 'object' && 'start' in value) {
    return value
  }
  return { start: null, end: null }
})
const pickingEnd = computed<boolean>(
  () => props.mode === 'range' && rangeValue.value.start !== null && rangeValue.value.end === null
)
const hoverPreview = computed<CalendarDate | null>(() =>
  pickingEnd.value ? hoverDate.value : null
)

// --- auto-reveal of the selection ----------------------------------------------
function targetBase(initialRender: boolean): number {
  const first = monthIndex(firstVisibleMonth.value)
  const last = first + props.grids - 1
  const todayIdx = monthIndex(today(props.settings.timeZone))

  function isFullyVisible(startIdx: number, endIdx: number): boolean {
    return startIdx >= first && endIdx <= last
  }

  function leftFreeGrids(startIdx: number, endIdx: number): number {
    const span = endIdx - startIdx + 1
    const free = props.grids - span

    if (free <= 0) {
      return 0
    }
    if (free % 2 === 0) {
      return free / 2
    }
    // put the extra grid on the left only when the whole interval is strictly in the future
    const extraOnLeft = startIdx > todayIdx
    return Math.floor(free / 2) + (extraOnLeft ? 1 : 0)
  }

  function targetBaseForInterval(startIdx: number, endIdx: number): number {
    const span = endIdx - startIdx + 1

    if (span > props.grids) {
      return endIdx - (props.grids - 1) // larger than displayable: end in the last grid
    }

    if (!initialRender && isFullyVisible(startIdx, endIdx)) {
      return first // for updates: don't shift if we're already showing the interval
    }

    // center, with unused grids biased towards today
    return startIdx - leftFreeGrids(startIdx, endIdx)
  }

  if (props.mode === 'single') {
    const anchor = singleValue.value ?? today(props.settings.timeZone)
    const idx = monthIndex(anchor)
    return targetBaseForInterval(idx, idx)
  }

  const { start, end } = rangeValue.value
  if (start === null) {
    if (!initialRender) {
      return first
    }
    return todayIdx - leftFreeGrids(todayIdx, todayIdx)
  }

  const startIdx = monthIndex(start)
  if (end === null) {
    return targetBaseForInterval(startIdx, startIdx)
  }

  const endIdx = monthIndex(end)
  return targetBaseForInterval(startIdx, endIdx)
}

function ensureVisible(initialRender = false): void {
  const target = targetBase(initialRender)
  if (target !== monthIndex(firstVisibleMonth.value)) {
    firstVisibleMonth.value = monthFromIndex(target)
  }
}

// Position the window and seed keyboard focus synchronously so the very first render is already
// correct (the flyout mounts this fresh on every open). Afterward, only an off-screen selection
// set from outside (e.g. a preset) moves the window.
ensureVisible(true)
focusedDate.value = singleValue.value ?? rangeValue.value.start ?? today(props.settings.timeZone)

watch(selection, () => ensureVisible(false))

// --- interaction ----------------------------------------------------------------
function onSelect(date: CalendarDate): void {
  if (props.mode === 'single') {
    selection.value = date as SelectionFor<M>
    focusedDate.value = date
    return
  }

  const { start, end } = rangeValue.value
  if (start === null || end !== null) {
    // begin a new range — selection not yet complete
    selection.value = { start: date, end: null } as SelectionFor<M>
  } else {
    const ordered = date.compare(start) < 0 ? { start: date, end: start } : { start, end: date }
    selection.value = ordered as SelectionFor<M>
  }
  hoverDate.value = null
  focusedDate.value = date
}

function onHover(date: CalendarDate | null): void {
  if (pickingEnd.value) {
    hoverDate.value = date
  }
}

function onFocusedDate(date: CalendarDate): void {
  focusedDate.value = date
  const base = monthIndex(firstVisibleMonth.value)
  const idx = monthIndex(date)
  if (idx < base) {
    firstVisibleMonth.value = monthFromIndex(idx)
  } else if (idx > base + props.grids - 1) {
    firstVisibleMonth.value = monthFromIndex(idx - (props.grids - 1))
  }
}

function goToPrev(): void {
  firstVisibleMonth.value = firstVisibleMonth.value.subtract({ months: 1 })
}
function goToNext(): void {
  firstVisibleMonth.value = firstVisibleMonth.value.add({ months: 1 })
}
function setGridMonth(index: number, month: number): void {
  firstVisibleMonth.value = visibleMonths.value[index]!.set({ month }).subtract({ months: index })
}
function setGridYear(index: number, year: number): void {
  firstVisibleMonth.value = visibleMonths.value[index]!.set({ year }).subtract({ months: index })
}

const rootRef = useTemplateRef<HTMLElement>('root')

/**
 * The month/year of the focused date, voiced by the live region. Keyboard navigation that changes
 * the displayed month (PageUp/PageDown, or an arrow/Home/End crossing a month boundary) updates the
 * grid in place, which does not re-announce its name — this region fills that gap. Because the text
 * only changes when the month or year changes, same-month navigation is naturally not re-announced.
 */
const monthYearText = computed<TranslatedString>(() => {
  const date = focusedDate.value
  if (date === null) {
    return untranslated('')
  }
  return props.settings.formatMonthYear(date)
})

/**
 * Move DOM focus onto the focused day's button. The owner calls this when the calendar is opened
 * via an explicit "open" affordance (e.g. the picker's icon button), landing the keyboard user on
 * the current date; opening by typing in the trigger field deliberately leaves focus in the field.
 */
function focus(): void {
  const date = focusedDate.value
  if (date === null) {
    return
  }
  rootRef.value?.querySelector<HTMLElement>(`[data-date="${date.toString()}"]`)?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div ref="root" class="cmk-date-calendar">
    <CmkVisuallyHidden :text="monthYearText" live="polite" />
    <div v-for="(month, i) in visibleMonths" :key="i" class="cmk-date-calendar__column">
      <CalendarControls
        class="cmk-date-calendar__controls"
        :month="month.month"
        :year="month.year"
        :month-names-display="settings.monthNamesShort"
        :year-range="effectiveYearRange"
        :show-prev="i === 0"
        :show-next="i === grids - 1"
        @prev="goToPrev"
        @next="goToNext"
        @update:month="(value) => setGridMonth(i, value)"
        @update:year="(value) => setGridYear(i, value)"
      />
      <CalendarGrid
        v-if="mode === 'single'"
        mode="single"
        :display-date="month"
        :settings="settings"
        :focused-date="focusedDate"
        :selection="singleValue"
        @select="onSelect"
        @update:focused-date="onFocusedDate"
      />
      <CalendarGrid
        v-else
        mode="range"
        :display-date="month"
        :settings="settings"
        :focused-date="focusedDate"
        :selection="rangeValue"
        :hover-preview="hoverPreview"
        @select="onSelect"
        @hover="onHover"
        @update:focused-date="onFocusedDate"
      />
    </div>
    <div v-if="$slots.aside" class="cmk-date-calendar__aside">
      <slot name="aside" />
    </div>
  </div>
</template>

<style scoped>
.cmk-date-calendar {
  display: grid;
  grid-template-rows: auto auto;
  grid-auto-flow: column;
  grid-auto-columns: max-content;
  gap: var(--dimension-4) var(--dimension-6);
  align-items: start;
}

.cmk-date-calendar__column {
  display: contents;
}

.cmk-date-calendar__aside {
  grid-row: 2;
}
</style>
