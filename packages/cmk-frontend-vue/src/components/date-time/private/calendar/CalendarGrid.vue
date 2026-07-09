<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CalendarDate } from '@internationalized/date'
import { isSameDay, startOfMonth, today } from '@internationalized/date'
import { computed, useTemplateRef, watch } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { ResolvedDateTimeSettings, Weekday } from '../../types'
import type { CalendarSelection } from './types'
import { navTarget, weekdayOf } from './util'

interface CalendarGridBaseProps {
  /** Which year & month is shown, day is ignored. */
  displayDate: CalendarDate
  /** Resolved locale settings: week start, weekend days, weekday names, timezone, and formatters. */
  settings: ResolvedDateTimeSettings
  /** Currently focused date, used for keyboard navigation */
  focusedDate?: CalendarDate | null
}

/**
 * `mode` discriminates the shape of `selection`: a single `CalendarDate | null` in `'single'`
 * mode, the two-endpoint `CalendarSelection` in `'range'` mode. `hoverPreview` only applies to
 * range mode.
 */
type CalendarGridProps = CalendarGridBaseProps &
  (
    | {
        /** Controls if this calendar shows a single selected date or a range */
        mode: 'single'
        /** The currently selected date */
        selection: CalendarDate | null
      }
    | {
        mode: 'range'
        /** The currently selected range endpoints */
        selection: CalendarSelection
        /** Currently hovered date, used to preview the range across multiple calendar grids */
        hoverPreview?: CalendarDate | null
      }
  )

const props = defineProps<CalendarGridProps>()

const emit = defineEmits<{
  /** A day was activated (click / Enter / Space). */
  (e: 'select', date: CalendarDate): void
  /** The hovered day changed (`null` when the pointer leaves the grid); drives the range preview. */
  (e: 'hover', date: CalendarDate | null): void
  /** Keyboard navigation moved the focused date; the parent owns which month(s) are shown. */
  (e: 'update:focusedDate', date: CalendarDate): void
}>()

const { _t } = usei18n()

const gridElement = useTemplateRef('grid')

/** The grid's accessible name: the displayed month and year (e.g. "June 2026"), locale-ordered. */
const gridLabel = computed<TranslatedString>(() =>
  props.settings.formatMonthYear(props.displayDate)
)

const weekdayColumns = computed(() =>
  Array.from({ length: 7 }, (_unused, index) => {
    const weekday = ((props.settings.firstDayOfWeek + index) % 7) as Weekday
    return {
      name: props.settings.weekdayNamesNarrow[weekday],
      accessibleName: props.settings.weekdayNamesLong[weekday],
      isWeekend: props.settings.weekendDays.includes(weekday)
    }
  })
)

/** The two ordered endpoints of the active range, treating a hover preview as a tentative end. */
const rangeBounds = computed<{ min: CalendarDate; max: CalendarDate } | null>(() => {
  if (props.mode !== 'range' || props.selection.start === null) {
    return null
  }
  const start = props.selection.start
  const other = props.selection.end ?? props.hoverPreview ?? null
  if (other === null) {
    return { min: start, max: start }
  }
  return start.compare(other) <= 0 ? { min: start, max: other } : { min: other, max: start }
})

interface DayCell {
  date: CalendarDate
  key: string
  inCurrentMonth: boolean
  isToday: boolean
  /** Single-mode: the selected day. Range-mode: a range endpoint (start or end). */
  isSelected: boolean
  isInRange: boolean
  isFocusable: boolean
  isWeekend: boolean
  /** Visible day number, e.g. `"10"`. */
  label: string
  /** Spoken name for the day button: the full localized date, plus the range role for endpoints. */
  accessibleLabel: TranslatedString
}

const cells = computed<DayCell[]>(() => {
  const firstOfMonth = startOfMonth(props.displayDate)
  const leadingOffset = (weekdayOf(firstOfMonth) - props.settings.firstDayOfWeek + 7) % 7
  const gridStart = firstOfMonth.subtract({ days: leadingOffset })
  const todayDate = today(props.settings.timeZone)
  const bounds = rangeBounds.value

  // 6 weeks * 7 days = 42 cells
  return Array.from({ length: 42 }, (_unused, index): DayCell => {
    const date = gridStart.add({ days: index })
    const inCurrentMonth =
      date.month === props.displayDate.month && date.year === props.displayDate.year

    let isSelected = false
    let isInRange = false
    if (props.mode === 'single') {
      isSelected = props.selection !== null && isSameDay(date, props.selection)
    } else if (bounds !== null) {
      isSelected = isSameDay(date, bounds.min) || isSameDay(date, bounds.max)
      isInRange = date.compare(bounds.min) > 0 && date.compare(bounds.max) < 0
    }

    // The full date names the day button; range endpoints also announce their role.
    let accessibleLabel = props.settings.formatLongDate(date)
    if (props.mode === 'range' && bounds !== null && inCurrentMonth) {
      if (isSameDay(date, bounds.min)) {
        accessibleLabel = untranslated(`${accessibleLabel}, ${_t('range start')}`)
      } else if (isSameDay(date, bounds.max)) {
        accessibleLabel = untranslated(`${accessibleLabel}, ${_t('range end')}`)
      }
    }

    return {
      date,
      key: date.toString(),
      inCurrentMonth,
      isToday: isSameDay(date, todayDate),
      isSelected,
      isInRange,
      isFocusable:
        props.focusedDate !== null &&
        props.focusedDate !== undefined &&
        isSameDay(date, props.focusedDate) &&
        inCurrentMonth,
      isWeekend: props.settings.weekendDays.includes(weekdayOf(date)),
      label: `${date.day}`,
      accessibleLabel
    }
  })
})

/** The 42 cells grouped into 6 weeks of 7, so each renders as an ARIA `role="row"`. */
const weeks = computed<DayCell[][]>(() =>
  Array.from({ length: 6 }, (_unused, week) => cells.value.slice(week * 7, week * 7 + 7))
)

/**
 * Map a key press on a day to an action. Enter/Space select; the navigation keys (arrows, Home/End,
 * PageUp/PageDown, with Shift for year steps) resolve to a target date via {@link navTarget} and
 * emit it. The parent owns `focusedDate` and which month(s) are shown; whichever grid then renders
 * the target date focuses it (see below).
 */
function onDayKey(event: KeyboardEvent, date: CalendarDate): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('select', date)
    return
  }
  const target = navTarget(event.key, event.shiftKey, date, props.settings.firstDayOfWeek)
  if (target !== null) {
    event.preventDefault()
    emit('update:focusedDate', target)
  }
}

/**
 * Focus the day cell for `date` if this grid renders it. Only in-month days are
 * `<button>`s carrying `data-date`; adjacent-month placeholders are not, so this is a
 * natural no-op for dates outside the displayed month (e.g. the sibling grid's month).
 */
function focusCell(date: CalendarDate): void {
  const el = gridElement.value?.querySelector<HTMLButtonElement>(`[data-date="${date.toString()}"]`)
  el?.focus()
}

// Follow the focused date with actual DOM focus *only when it changes* (keyboard navigation) —
// never on mount, so opening the flyout doesn't steal focus from the trigger the user is typing
// in. The roving `tabindex=0` still lets a keyboard user Tab into the grid when they want it.
// `flush: 'post'` runs after the DOM re-renders, so when the parent also switches the displayed
// month the target cell exists before we focus it.
watch(
  () => props.focusedDate,
  (date) => {
    if (date) {
      focusCell(date)
    }
  },
  { flush: 'post' }
)
</script>

<template>
  <div
    ref="grid"
    class="cmk-calendar-grid"
    role="grid"
    :aria-label="gridLabel"
    @mouseleave="emit('hover', null)"
  >
    <div class="cmk-calendar-grid__row" role="row">
      <span
        v-for="(column, index) in weekdayColumns"
        :key="`head-${index}`"
        class="cmk-calendar-grid__weekday"
        :class="{ 'cmk-calendar-grid__weekday--weekend': column.isWeekend }"
        role="columnheader"
        :aria-label="column.accessibleName"
        @mouseenter="emit('hover', null)"
      >
        {{ column.name }}
      </span>
    </div>

    <div
      v-for="(week, weekIndex) in weeks"
      :key="`week-${weekIndex}`"
      class="cmk-calendar-grid__row"
      role="row"
    >
      <div
        v-for="cell in week"
        :key="cell.key"
        class="cmk-calendar-grid__cell"
        :class="{ 'cmk-calendar-grid__cell--weekend': cell.isWeekend }"
        role="gridcell"
        :aria-selected="cell.inCurrentMonth ? cell.isSelected : undefined"
        :aria-current="cell.inCurrentMonth && cell.isToday ? 'date' : undefined"
        @mouseenter="emit('hover', cell.inCurrentMonth ? cell.date : null)"
      >
        <button
          v-if="cell.inCurrentMonth"
          type="button"
          :data-date="cell.key"
          class="cmk-calendar-grid__day"
          :class="{
            'cmk-calendar-grid__day--today': cell.isToday,
            'cmk-calendar-grid__day--selected': cell.isSelected,
            'cmk-calendar-grid__day--in-range': cell.isInRange
          }"
          :tabindex="cell.isFocusable ? 0 : -1"
          :aria-label="cell.accessibleLabel"
          @click="emit('select', cell.date)"
          @keydown="onDayKey($event, cell.date)"
        >
          {{ cell.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cmk-calendar-grid {
  --day-size: var(--dimension-9);
  --cmk-calendar-column-bg: var(--color-daylight-grey-40);
  --cmk-calendar-fg: var(--color-conference-grey-100);
  --cmk-calendar-hover-bg: var(--color-conference-grey-10);
  --cmk-calendar-in-range-bg: var(--color-corporate-green-10);
  --cmk-calendar-selected-bg: var(--color-corporate-green-50);
  --cmk-calendar-selected-fg: var(--color-conference-grey-100);
  --cmk-calendar-selected-border: var(--color-corporate-green-70);
  --cmk-calendar-today-border: var(--color-mid-grey-60);
  --cmk-calendar-today-selected-border: var(--color-conference-grey-100);

  display: grid;
  grid-template-columns: repeat(7, var(--day-size));
  width: max-content;
  user-select: none;
}

/* Each ARIA row spans the 7 day columns and borrows the parent's column tracks via subgrid, so
   every cell stays aligned to its weekday column without a second source of truth for the widths. */
.cmk-calendar-grid__row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
}

body[data-theme='modern-dark'] .cmk-calendar-grid {
  --cmk-calendar-column-bg: var(--color-midnight-grey-60);
  --cmk-calendar-fg: var(--color-white-100);
  --cmk-calendar-hover-bg: var(--color-white-10);
  --cmk-calendar-in-range-bg: var(--color-corporate-green-90);
  --cmk-calendar-selected-bg: var(--color-corporate-green-50);
  --cmk-calendar-selected-fg: var(--color-conference-grey-100);
  --cmk-calendar-selected-border: var(--color-corporate-green-50);
  --cmk-calendar-today-border: var(--color-mid-grey-60);
  --cmk-calendar-today-selected-border: var(--color-white-100);
}

.cmk-calendar-grid__weekday {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--day-size);
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

/* The gridcell carries the continuous weekday-column band as its background and centers the day
   button; empty (adjacent-month) cells keep the row height so the band tiles without gaps. */
.cmk-calendar-grid__cell {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--day-size);
}

.cmk-calendar-grid__weekday,
.cmk-calendar-grid__cell {
  background: var(--cmk-calendar-column-bg);
}

.cmk-calendar-grid__weekday--weekend,
.cmk-calendar-grid__cell--weekend {
  background: transparent;
}

.cmk-calendar-grid__day {
  /* border-box so the 1px selected/today border stays inside --day-size and the day fills its cell. */
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--day-size);
  height: var(--day-size);
  margin: 0;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--dimension-2);
  background: transparent;
  color: var(--cmk-calendar-fg);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  font-variant-numeric: tabular-nums;
  box-shadow: none;

  &.cmk-calendar-grid__day--in-range {
    background: var(--cmk-calendar-in-range-bg);
    border-radius: 0;
  }

  &.cmk-calendar-grid__day--selected {
    color: var(--cmk-calendar-selected-fg);
    background: var(--cmk-calendar-selected-bg);
    border-color: var(--cmk-calendar-selected-border);

    &.cmk-calendar-grid__day--today {
      border-color: var(--cmk-calendar-today-selected-border);
    }
  }

  &.cmk-calendar-grid__day--today {
    border-color: var(--cmk-calendar-today-border);
  }
}

button.cmk-calendar-grid__day {
  cursor: pointer;

  &:hover {
    box-shadow: inset 0 0 0 999px var(--cmk-calendar-hover-bg);
  }

  &:focus-visible {
    outline: revert;
  }
}
</style>
