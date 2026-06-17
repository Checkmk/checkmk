/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Small converters mapping the string-valued showcase knobs to the picker prop values.
 */
import type { HourCycle } from '@/components/date-time'

/**
 * Shared properties-panel knob definitions for the date/time pickers. Defining them once here (and
 * composing each page's `panelConfig` from the relevant subset) keeps the option lists identical
 * across pages, so a picker can never silently omit a setting it actually supports.
 */
export const dateFormatKnob = {
  type: 'list' as const,
  title: 'Date format',
  options: [
    { title: 'Locale-derived', name: 'locale' },
    { title: 'ISO (YYYY-MM-DD)', name: 'iso' }
  ],
  initialState: 'locale'
}

export const hourCycleKnob = {
  type: 'list' as const,
  title: 'Hour cycle',
  options: [
    { title: 'Locale-derived', name: 'locale' },
    { title: '24-hour', name: '24' },
    { title: '12-hour (AM/PM)', name: '12' },
    { title: '12-hour, zero-based (h11)', name: '11' }
  ],
  initialState: 'locale'
}

export const firstDayOfWeekKnob = {
  type: 'list' as const,
  title: 'First day of week',
  options: [
    { title: 'Locale-derived', name: 'locale' },
    { title: 'Monday', name: '1' },
    { title: 'Sunday', name: '0' },
    { title: 'Saturday', name: '6' }
  ],
  initialState: 'locale'
}

export const weekendDaysKnob = {
  type: 'list' as const,
  title: 'Weekend days',
  options: [
    { title: 'Saturday & Sunday', name: 'sat-sun' },
    { title: 'Friday & Saturday', name: 'fri-sat' },
    { title: 'None', name: 'none' }
  ],
  initialState: 'sat-sun'
}

export const saveModeKnob = { type: 'boolean' as const, title: 'Save mode', initialState: false }

export const disabledKnob = { type: 'boolean' as const, title: 'Disabled', initialState: false }

export const nullableKnob = { type: 'boolean' as const, title: 'Nullable', initialState: false }

export const presetsKnob = { type: 'boolean' as const, title: 'Presets', initialState: false }

export function resolveHourCycleKnob(value: string): HourCycle | undefined {
  if (value === '11') {
    return 11
  }
  if (value === '12') {
    return 12
  }
  if (value === '24') {
    return 24
  }
  return undefined
}
