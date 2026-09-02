/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { parseAbsolute, toZoned } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, test, vi } from 'vitest'
import { nextTick } from 'vue'

import ScheduleDowntimeForm, {
  type DowntimePresetOption,
  type DowntimeRecurrenceOption,
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues,
  downtimeWindow,
  isScheduleDowntimeValid,
  presetSelection,
  untilPresetEnd
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'

/** What a site offers out of the box, as `user_downtime_timeranges` has it. */
const PRESETS: DowntimePresetOption[] = [
  { title: '2 hours', end: 2 * 60 * 60 },
  { title: 'Today', end: 'next_day' },
  { title: 'This week', end: 'next_week' },
  { title: 'This month', end: 'next_month' },
  { title: 'This year', end: 'next_year' }
]

function mountForm(
  overrides: Partial<ScheduleDowntimeFormValues> = {},
  recurrences: DowntimeRecurrenceOption[] = [],
  presetsUrl: string | null = null,
  presets: DowntimePresetOption[] = PRESETS
) {
  const modelValue: ScheduleDowntimeFormValues = {
    ...defaultScheduleDowntimeValues(presets),
    ...overrides
  }
  return {
    ...render(ScheduleDowntimeForm, { props: { modelValue, recurrences, presets, presetsUrl } }),
    modelValue
  }
}

// jsdom has neither ResizeObserver nor layout, so stub the observer (its callback is the overflow
// composable's recompute, invoked directly below) and hand the row its geometry by hand.
class FakeResizeObserver {
  static instances: FakeResizeObserver[] = []
  constructor(public callback: ResizeObserverCallback) {
    FakeResizeObserver.instances.push(this)
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

/** Every duration the form offers, in render order, to tell chips from the form's other buttons. */
const DURATION_LABELS = ['Custom', 'Now', ...PRESETS.map((preset) => preset.title)]

function stubGeometry(el: HTMLElement, props: Record<string, number>): void {
  for (const [key, value] of Object.entries(props)) {
    Object.defineProperty(el, key, { value, configurable: true })
  }
}

/**
 * Give every measured chip the same width and the row only enough of it for `visible` chips plus the
 * dropdown trigger, then run a resize. Chip n's right edge is (n + 1) * CHIP, the trigger reserves
 * one CHIP, so a row of (visible + 1) * CHIP admits exactly `visible` chips.
 */
function squeezeChipRow(container: Element, visible: number): void {
  const CHIP = 100
  const row = container.querySelector<HTMLElement>('.monitoring-schedule-downtime-form__chips')!
  const measure = container.querySelector<HTMLElement>(
    '.monitoring-schedule-downtime-form__chips-measure'
  )!
  const children = Array.from(measure.children) as HTMLElement[]
  const chips = children.slice(0, -1)
  chips.forEach((chip, index) =>
    stubGeometry(chip, { offsetLeft: 0, offsetWidth: (index + 1) * CHIP })
  )
  stubGeometry(children.at(-1)!, { offsetLeft: chips.length * CHIP, offsetWidth: CHIP })
  stubGeometry(row, { clientWidth: (visible + 1) * CHIP })

  const observer = FakeResizeObserver.instances.at(-1)!
  observer.callback([], observer as unknown as ResizeObserver)
}

test('is invalid until a comment is provided', async () => {
  const { emitted } = mountForm()

  expect(emitted('update:valid')?.at(-1)).toEqual([false])

  await userEvent.type(screen.getByPlaceholderText('What is the occasion?'), 'maintenance')
  expect(emitted('update:valid')?.at(-1)).toEqual([true])
})

test('reveals the advanced options when the section is expanded', async () => {
  mountForm({ comment: 'maintenance' })

  const childHosts = screen.getByText('Only for hosts: Set child hosts in downtime.')
  expect(childHosts).not.toBeVisible()

  await userEvent.click(screen.getByRole('button', { name: /Advanced option/ }))
  expect(childHosts).toBeVisible()
})

test("the immediate duration chip is named 'Now'", () => {
  mountForm({ comment: 'maintenance' })

  expect(screen.getByRole('button', { name: 'Now' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Ad hoc' })).not.toBeInTheDocument()
})

test('marks the selected duration chip as pressed', async () => {
  mountForm({ comment: 'maintenance', selection: presetSelection(0) })

  expect(screen.getByRole('button', { name: '2 hours', pressed: true })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Today', pressed: false })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Today' }))
  expect(screen.getByRole('button', { name: 'Today', pressed: true })).toBeInTheDocument()
})

test('offers the durations the site configured, not a hard-coded set', () => {
  mountForm({ comment: 'maintenance' }, [], null, [
    { title: '30 minutes', end: 30 * 60 },
    { title: 'Until tomorrow', end: 'next_day' }
  ])

  expect(screen.getByRole('button', { name: '30 minutes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Until tomorrow' })).toBeInTheDocument()
  // The form's own two stay; everything else is the site's to decide.
  expect(screen.getByRole('button', { name: 'Custom' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Now' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '2 hours' })).not.toBeInTheDocument()
})

test('links the duration presets only when the server offers the page', () => {
  const { unmount } = mountForm({ comment: 'maintenance' }, [], 'wato.py?mode=edit_configvar')

  const link = screen.getByRole('link', { name: '(edit presets)' })
  expect(link).toHaveAttribute('href', 'wato.py?mode=edit_configvar')
  // A new tab, so the comment and duration the user already picked survive the detour.
  expect(link).toHaveAttribute('target', '_blank')
  unmount()

  mountForm({ comment: 'maintenance' })
  expect(screen.queryByRole('link', { name: '(edit presets)' })).not.toBeInTheDocument()
})

test('a duration preset explains itself as a duration', () => {
  mountForm({ comment: 'maintenance', selection: presetSelection(0) })

  expect(
    screen.getByText('Scheduled downtime, starting now with a duration of 2 hours.')
  ).toBeInTheDocument()
})

test('an until preset explains itself with the end date', () => {
  mountForm({ comment: 'maintenance', selection: presetSelection(1) })

  expect(screen.getByText(/Scheduled downtime, starting now and ending on/)).toBeInTheDocument()
})

describe('a row too narrow for every duration', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  })

  afterEach(() => {
    FakeResizeObserver.instances = []
    vi.unstubAllGlobals()
  })

  it('narrows the row further than the count cap already does', async () => {
    const { container } = mountForm({ comment: 'maintenance' })

    // The cap alone leaves seven chips (see the count test below); squeezing leaves two.
    squeezeChipRow(container, 2)
    await nextTick()

    expect(screen.getByRole('button', { name: 'Custom' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Now' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '2 hours' })).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'More durations' })).toBeInTheDocument()
  })

  it('applies a duration picked from the dropdown', async () => {
    const { container, modelValue } = mountForm({ comment: 'maintenance' })

    squeezeChipRow(container, 2)
    await nextTick()

    await userEvent.click(screen.getByRole('combobox', { name: 'More durations' }))
    await userEvent.click(screen.getByRole('option', { name: 'This year' }))

    // 'This year' is the last of the five configured ranges, so the fifth preset chip.
    expect(modelValue.selection).toBe(presetSelection(4))
  })
})

test('shows the durations a stock site offers without needing the dropdown', () => {
  mountForm({ comment: 'maintenance' })

  const chips = screen
    .getAllByRole('button')
    .map((chip) => chip.textContent?.trim())
    .filter((label) => DURATION_LABELS.includes(label!))

  // 'Custom' and 'Now' plus the five ranges a fresh site configures is exactly the cap.
  expect(chips).toEqual([
    'Custom',
    'Now',
    '2 hours',
    'Today',
    'This week',
    'This month',
    'This year'
  ])
  expect(screen.queryByRole('combobox', { name: 'More durations' })).not.toBeInTheDocument()
})

test('hides the durations past the cap behind the dropdown', async () => {
  const extra: DowntimePresetOption[] = [...PRESETS, { title: '10 days', end: 10 * 24 * 60 * 60 }]
  mountForm({ comment: 'maintenance' }, [], null, extra)

  const chips = screen
    .getAllByRole('button')
    .map((chip) => chip.textContent?.trim())
    .filter((label) => ['Custom', 'Now', ...extra.map((preset) => preset.title)].includes(label!))
  expect(chips).toEqual([
    'Custom',
    'Now',
    '2 hours',
    'Today',
    'This week',
    'This month',
    'This year'
  ])

  await userEvent.click(screen.getByRole('combobox', { name: 'More durations' }))
  expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
    '10 days'
  ])
})

describe('isScheduleDowntimeValid', () => {
  it('requires a non-empty comment', () => {
    expect(
      isScheduleDowntimeValid({ ...defaultScheduleDowntimeValues(PRESETS), comment: '' }, PRESETS)
    ).toBe(false)
    expect(
      isScheduleDowntimeValid({ ...defaultScheduleDowntimeValues(PRESETS), comment: 'x' }, PRESETS)
    ).toBe(true)
  })

  it('rejects a zero ad hoc duration', () => {
    expect(
      isScheduleDowntimeValid(
        {
          ...defaultScheduleDowntimeValues(PRESETS),
          comment: 'x',
          selection: 'adhoc',
          adhocHours: 0,
          adhocMinutes: 0
        },
        PRESETS
      )
    ).toBe(false)
  })
})

describe('downtimeWindow', () => {
  it('spans the preset duration for a preset selection', () => {
    const window = downtimeWindow(defaultScheduleDowntimeValues(PRESETS), PRESETS)

    expect(window).not.toBeNull()
    const spanMs = new Date(window!.end).getTime() - new Date(window!.start).getTime()
    expect(spanMs).toBe(2 * 60 * 60_000)
  })

  it('returns null for an empty ad hoc duration', () => {
    const window = downtimeWindow(
      {
        ...defaultScheduleDowntimeValues(PRESETS),
        selection: 'adhoc',
        adhocHours: 0,
        adhocMinutes: 0
      },
      PRESETS
    )

    expect(window).toBeNull()
  })

  it.each(
    PRESETS.map((preset, index) => ({ ...preset, index })).filter(
      ({ end }) => typeof end === 'string'
    )
  )('ends on a later calendar boundary for $title', ({ index }) => {
    const window = downtimeWindow(
      { ...defaultScheduleDowntimeValues(PRESETS), selection: presetSelection(index) },
      PRESETS
    )

    expect(window).not.toBeNull()
    expect(new Date(window!.end).getTime()).toBeGreaterThan(new Date(window!.start).getTime())
  })
})

describe('untilPresetEnd', () => {
  const start = toZoned(parseAbsolute('2026-08-04T10:30:00Z', 'UTC'), 'UTC')

  it('ends at the start of the next day for today', () => {
    expect(untilPresetEnd('next_day', start).toString()).toBe('2026-08-05T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the day after the coming Sunday for the week', () => {
    expect(untilPresetEnd('next_week', start).toString()).toBe('2026-08-10T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the next month', () => {
    expect(untilPresetEnd('next_month', start).toString()).toBe('2026-09-01T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the next year', () => {
    expect(untilPresetEnd('next_year', start).toString()).toBe('2027-01-01T00:00:00+00:00[UTC]')
  })
})

describe('Repeat', () => {
  const RECURRENCES: DowntimeRecurrenceOption[] = [
    { recur: 'fixed', title: 'never' },
    { recur: 'day', title: 'day' },
    { recur: 'day_of_month', title: 'same day of the month' }
  ]

  it('offers every interval the page was told the site has', async () => {
    mountForm({ comment: 'maintenance' }, RECURRENCES)

    await userEvent.click(screen.getByRole('combobox', { name: 'Repeat' }))

    expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
      'never',
      'day',
      'same day of the month'
    ])
  })

  /** A site whose edition repeats no downtime still has the one interval every core can do. */
  it('offers never alone when the page was told of no interval', async () => {
    mountForm({ comment: 'maintenance' })

    await userEvent.click(screen.getByRole('combobox', { name: 'Repeat' }))

    expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
      'never'
    ])
  })

  it('carries the chosen interval in the form values, for the request to take', async () => {
    const { modelValue } = mountForm({ comment: 'maintenance' }, RECURRENCES)

    await userEvent.click(screen.getByRole('combobox', { name: 'Repeat' }))
    await userEvent.click(screen.getByRole('option', { name: 'day' }))

    expect(modelValue.recur).toBe('day')
  })

  /**
   * The classic view rejects the same thing: a downtime repeating on a day the short months do
   * not have would skip them.
   */
  it('is invalid when a monthly repeat starts after the 28th', () => {
    const start = toZoned(parseAbsolute('2026-08-29T10:00:00Z', 'UTC'), 'UTC')

    expect(
      isScheduleDowntimeValid(
        {
          ...defaultScheduleDowntimeValues(PRESETS),
          comment: 'maintenance',
          selection: 'custom',
          customRange: { from: start, to: start.add({ hours: 4 }) },
          recur: 'day_of_month'
        },
        PRESETS
      )
    ).toBe(false)
  })

  it('is valid when a monthly repeat starts on a day every month has', () => {
    const start = toZoned(parseAbsolute('2026-08-28T10:00:00Z', 'UTC'), 'UTC')

    expect(
      isScheduleDowntimeValid(
        {
          ...defaultScheduleDowntimeValues(PRESETS),
          comment: 'maintenance',
          selection: 'custom',
          customRange: { from: start, to: start.add({ hours: 4 }) },
          recur: 'day_of_month'
        },
        PRESETS
      )
    ).toBe(true)
  })

  it('says why a monthly repeat is refused', async () => {
    const start = toZoned(parseAbsolute('2026-08-29T10:00:00Z', 'UTC'), 'UTC')
    mountForm(
      {
        comment: 'maintenance',
        selection: 'custom',
        customRange: { from: start, to: start.add({ hours: 4 }) },
        recur: 'day_of_month'
      },
      RECURRENCES
    )

    expect(
      await screen.findByText(
        'A downtime repeating monthly has to start between the 1st and the 28th.'
      )
    ).toBeInTheDocument()
  })
})
