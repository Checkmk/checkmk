/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, shallowRef } from 'vue'

import GlobalTimePicker from '@/graphing/GlobalTimePicker/GlobalTimePicker.vue'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

const TZ = 'Europe/Berlin'

// A range of exactly `totalSeconds`, anchored at a fixed instant so durations are deterministic.
const rangeOfSeconds = (totalSeconds: number): DateTimeRange => {
  const to: ZonedDateTime = toZoned(new CalendarDateTime(2026, 3, 10, 12, 0), TZ, 'compatible')
  return { from: to.subtract({ seconds: totalSeconds }), to }
}

const CUSTOM_RANGES: CustomGraphTimeRange[] = [
  { title: 'Last 4 hours', total_seconds: 4 * 3600 },
  { title: 'Last 25 hours', total_seconds: 25 * 3600 }
]

function renderPicker(
  modelValue: DateTimeRange,
  firstDayOfWeek: 'saturday' | 'sunday' | 'monday' | null = null
) {
  const updates: DateTimeRange[] = []
  const view = render(GlobalTimePicker, {
    props: {
      customTimeRanges: CUSTOM_RANGES,
      serverTimeZone: TZ,
      firstDayOfWeek,
      modelValue,
      'onUpdate:modelValue': (value: DateTimeRange) => updates.push(value)
    }
  })
  const chip = (name: string) => screen.getByRole('button', { name })
  return { ...view, updates, chip }
}

/**
 * Feeds emitted ranges back into the model, so a range the test applies by hand reaches the
 * trigger. `renderPicker` deliberately does not, keeping the other tests' props fixed.
 */
function renderControlledPicker(modelValue: DateTimeRange) {
  const model = shallowRef(modelValue)
  const view = render(
    defineComponent({
      setup() {
        return () =>
          h(GlobalTimePicker, {
            customTimeRanges: CUSTOM_RANGES,
            serverTimeZone: TZ,
            firstDayOfWeek: null,
            modelValue: model.value,
            'onUpdate:modelValue': (value: DateTimeRange) => {
              model.value = value
            }
          })
      }
    })
  )
  return { ...view, currentModel: () => model.value }
}

/** The resolved display settings read the locale off `navigator`; jsdom offers no other switch. */
const mockLocale = (locale: string): void => {
  vi.spyOn(navigator, 'language', 'get').mockReturnValue(locale)
}

/** Scoped to this picker: a document-wide search would match any dialog trigger on screen. */
async function openFlyout(container: Element): Promise<void> {
  const trigger = container.querySelector<HTMLElement>(
    'button.graphing-global-time-picker__trigger'
  )
  expect(trigger, 'The picker rendered no flyout trigger').not.toBeNull()
  await fireEvent.click(trigger!)
}

const pad = (value: number): string => value.toString().padStart(2, '0')

/** Segments are addressed by name, so the locale's section order does not matter. */
async function setEndpoint(
  which: 'From' | 'To',
  parts: { year: number; month: number; day: number; hour: number; minute: number }
): Promise<void> {
  const date = within(screen.getByRole('group', { name: `${which} date` }))
  await fireEvent.update(date.getByRole('spinbutton', { name: 'Year' }), String(parts.year))
  await fireEvent.update(date.getByRole('spinbutton', { name: 'Month' }), pad(parts.month))
  await fireEvent.update(date.getByRole('spinbutton', { name: 'Day' }), pad(parts.day))
  const time = within(screen.getByRole('group', { name: `${which} time` }))
  await fireEvent.update(time.getByRole('spinbutton', { name: 'Hours' }), pad(parts.hour))
  await fireEvent.update(time.getByRole('spinbutton', { name: 'Minutes' }), pad(parts.minute))
}

/** In render order. The `aria-hidden` measurement replica is skipped by the role query;
 * `aria-pressed` then separates chips from the overflow control. */
function presetChipNames(container: Element): string[] {
  const band = container.querySelector<HTMLElement>('.graphing-dynamic-presets')!
  return within(band)
    .getAllByRole('button')
    .filter((button) => button.hasAttribute('aria-pressed'))
    .map((button) => button.textContent!.trim())
}

/** The trigger's own text, i.e. the range summary the user reads with the flyout closed. */
function triggerText(container: Element): string {
  return container.querySelector('.graphing-global-time-picker__trigger')!.textContent ?? ''
}

describe('GlobalTimePicker', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('renders a chip per configured custom range', () => {
    const { chip } = renderPicker(rangeOfSeconds(99))
    expect(chip('Last 4 hours')).toBeInTheDocument()
    expect(chip('Last 25 hours')).toBeInTheDocument()
  })

  test('highlights the chip matching the seeded range on load', () => {
    const { chip } = renderPicker(rollingRange(4 * 3600))
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'true')
    expect(chip('Last 25 hours')).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking a chip applies a range of its duration and marks it pressed', async () => {
    const { chip, updates } = renderPicker(rangeOfSeconds(99))
    await fireEvent.click(chip('Last 25 hours'))

    expect(updates).toHaveLength(1)
    const applied = updates[0]!
    const spanMs = applied.to.toDate().getTime() - applied.from.toDate().getTime()
    expect(spanMs).toBe(25 * 3600 * 1000)
    expect(chip('Last 25 hours')).toHaveAttribute('aria-pressed', 'true')
  })

  test('an external range change clears the pressed chip', async () => {
    const { chip, rerender } = renderPicker(rollingRange(4 * 3600))
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'true')

    await rerender({
      customTimeRanges: CUSTOM_RANGES,
      serverTimeZone: TZ,
      firstDayOfWeek: null,
      modelValue: rangeOfSeconds(99)
    })
    expect(chip('Last 4 hours')).toHaveAttribute('aria-pressed', 'false')
  })

  // jsdom's locale is en-US, so the browser-locale default is a Sunday week start.
  test.each([
    { firstDayOfWeek: 'monday' as const, expected: 'Monday' },
    { firstDayOfWeek: 'saturday' as const, expected: 'Saturday' },
    { firstDayOfWeek: null, expected: 'Sunday' }
  ])(
    'the calendar starts the week on $expected for preference $firstDayOfWeek',
    async ({ firstDayOfWeek, expected }) => {
      const { container } = renderPicker(rangeOfSeconds(99), firstDayOfWeek)
      await openFlyout(container)

      const grid = (await screen.findAllByRole('grid'))[0]!
      const firstColumnHeader = within(grid).getAllByRole('columnheader')[0]!
      expect(firstColumnHeader).toHaveAccessibleName(expected)
    }
  )

  test('the chips are exactly the configured ranges, in configured order', () => {
    const { container } = renderPicker(rangeOfSeconds(99))
    expect(presetChipNames(container)).toEqual(['Last 4 hours', 'Last 25 hours'])
  })

  test('a hand-typed range replaces the model and is what the trigger then reads', async () => {
    // A Monday-first, 24h locale, so the summary is checked against fixed digits.
    mockLocale('de-DE')
    const view = renderControlledPicker(rollingRange(4 * 3600))
    await openFlyout(view.container)

    await setEndpoint('From', { year: 2026, month: 3, day: 1, hour: 8, minute: 15 })
    await setEndpoint('To', { year: 2026, month: 3, day: 2, hour: 17, minute: 45 })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))

    const applied = view.currentModel()
    expect([applied.from.year, applied.from.month, applied.from.day]).toEqual([2026, 3, 1])
    expect([applied.from.hour, applied.from.minute]).toEqual([8, 15])
    expect([applied.to.year, applied.to.month, applied.to.day]).toEqual([2026, 3, 2])
    expect([applied.to.hour, applied.to.minute]).toEqual([17, 45])

    const summary = triggerText(view.container)
    expect(summary).toContain('01.03.2026')
    expect(summary).toContain('08:15')
    expect(summary).toContain('02.03.2026')
    expect(summary).toContain('17:45')
    // A hand-typed window is nobody's preset, so no chip stays highlighted.
    expect(view.container.querySelectorAll('[aria-pressed="true"]')).toHaveLength(0)
  })

  // Digits, not a fixed date: the host's zone shifts the calendar day. Separator and section
  // order are what is under test.
  test.each([
    { locale: 'de-DE', pattern: /(?<!\d)\d{2}\.\d{2}\.\d{4}(?!\d)/ },
    { locale: 'en-US', pattern: /(?<!\d)\d{2}\/\d{2}\/\d{4}(?!\d)/ }
  ])('the trigger writes dates in $locale notation', ({ locale, pattern }) => {
    mockLocale(locale)
    const { container } = renderPicker(rangeOfSeconds(99))
    expect(triggerText(container)).toMatch(pattern)
  })

  test('the trigger names its timezone and states the offset against UTC', () => {
    renderPicker(rangeOfSeconds(99))
    // The badge itself is aria-hidden; this is the text assistive tech is given instead.
    expect(screen.getByText(/^Timezone: /)).toHaveTextContent(/UTC/)
  })

  // 24-hour whatever the locale is, so no meridiem segment and no AM/PM in the summary.
  test.each(['de-DE', 'en-US'])('the %s time input names its two segments', async (locale) => {
    mockLocale(locale)
    const { container } = renderPicker(rangeOfSeconds(99))
    await openFlyout(container)

    const time = within(screen.getByRole('group', { name: 'From time' }))
    expect(time.getByRole('spinbutton', { name: 'Hours' })).toBeInTheDocument()
    expect(time.getByRole('spinbutton', { name: 'Minutes' })).toBeInTheDocument()
    expect(time.getAllByRole('spinbutton')).toHaveLength(2)
    expect(triggerText(container)).not.toMatch(/[AP]M/)
  })

  test.each([
    { locale: 'de-DE', expected: 'Montag' },
    { locale: 'en-US', expected: 'Sunday' }
  ])(
    'without a preference the $locale calendar starts the week on $expected',
    async ({ locale, expected }) => {
      mockLocale(locale)
      const { container } = renderPicker(rangeOfSeconds(99))
      await openFlyout(container)

      const grid = (await screen.findAllByRole('grid'))[0]!
      expect(within(grid).getAllByRole('columnheader')[0]!).toHaveAccessibleName(expected)
    }
  )

  test('a sunday preference overrides a locale that starts the week on Monday', async () => {
    mockLocale('de-DE')
    const { container } = renderPicker(rangeOfSeconds(99), 'sunday')
    await openFlyout(container)

    const grid = (await screen.findAllByRole('grid'))[0]!
    expect(within(grid).getAllByRole('columnheader')[0]!).toHaveAccessibleName('Sonntag')
  })
})
