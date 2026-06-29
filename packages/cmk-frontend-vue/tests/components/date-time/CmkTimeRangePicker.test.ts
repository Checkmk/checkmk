/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick, ref, shallowRef } from 'vue'

import CmkTimeRangePicker from '@/components/date-time/CmkTimeRangePicker.vue'
import type {
  DateTimePickerSettings,
  DateTimeRange,
  RangeDraft
} from '@/components/date-time/types'

import { TZ_BERLIN } from './dateTimeTestFixtures'
import { lastValue } from './pickerTestHarness'

// Explicit display settings so the tests never depend on the host locale. ISO date format renders
// the date segments year-month-day with '-' separators; 24h time avoids the meridiem segment.
const SETTINGS: DateTimePickerSettings = {
  hourCycle: 24,
  dateFormat: 'iso',
  firstDayOfWeek: 1,
  weekendDays: [0, 6]
}

// Build a Berlin-zoned instant from explicit wall-clock parts.
const berlin = (
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number
): ZonedDateTime =>
  toZoned(new CalendarDateTime(year, month, day, hour, minute), TZ_BERLIN, 'compatible')

/**
 * Render the picker through a self-tracking `modelValue`/`open` host, so committed writes and
 * open/close transitions are observable from the outside. Tests drive it only through the
 * accessible surface (roles + names).
 */
const renderPicker = (
  initial: DateTimeRange | null,
  extra: Record<string, unknown> = {},
  slots: Record<string, (...args: never[]) => unknown> = {}
) => {
  const model = shallowRef<DateTimeRange | null>(initial)
  const open = ref(false)
  const updates: Array<DateTimeRange | null> = []
  const openLog: boolean[] = []
  const view = render(
    defineComponent({
      setup() {
        return () =>
          h(
            CmkTimeRangePicker,
            {
              modelValue: model.value,
              open: open.value,
              settings: SETTINGS,
              timeZone: TZ_BERLIN,
              ...extra,
              'onUpdate:modelValue': (value: DateTimeRange | null) => {
                model.value = value
                updates.push(value)
              },
              'onUpdate:open': (value: boolean) => {
                open.value = value
                openLog.push(value)
              }
            },
            slots
          )
      }
    })
  )
  return {
    ...view,
    updates,
    openLog,
    currentModel: () => model.value,
    currentOpen: () => open.value
  }
}

type PickerView = ReturnType<typeof renderPicker>

const pad = (value: number): string => value.toString().padStart(2, '0')

const triggerButton = (view: PickerView) =>
  Array.from(view.container.querySelectorAll<HTMLButtonElement>('button')).find(
    (button) => button.getAttribute('aria-haspopup') === 'dialog'
  )!

async function openFlyout(view: PickerView) {
  await fireEvent.click(triggerButton(view))
  await nextTick()
}

const applyButton = (view: PickerView) => view.getByRole('button', { name: 'Apply' })

/** Type a date into one endpoint's segmented date field (ISO order, so any order of writes works). */
async function setDate(
  view: PickerView,
  which: 'From' | 'To',
  year: number,
  month: number,
  day: number
): Promise<void> {
  const group = within(view.getByRole('group', { name: `${which} date` }))
  await fireEvent.update(group.getByRole('spinbutton', { name: 'Year' }), String(year))
  await fireEvent.update(group.getByRole('spinbutton', { name: 'Month' }), pad(month))
  await fireEvent.update(group.getByRole('spinbutton', { name: 'Day' }), pad(day))
  await nextTick()
}

async function setTime(
  view: PickerView,
  which: 'From' | 'To',
  hour: number,
  minute: number
): Promise<void> {
  const group = within(view.getByRole('group', { name: `${which} time` }))
  await fireEvent.update(group.getByRole('spinbutton', { name: 'Hours' }), pad(hour))
  await fireEvent.update(group.getByRole('spinbutton', { name: 'Minutes' }), pad(minute))
  await nextTick()
}

/** The current displayed day digits of an endpoint's date field. */
const shownDay = (view: PickerView, which: 'From' | 'To'): string =>
  within(view.getByRole('group', { name: `${which} date` })).getByRole<HTMLInputElement>(
    'spinbutton',
    { name: 'Day' }
  ).value

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('CmkTimeRangePicker — default trigger', () => {
  test('renders the range summary and the dialog ARIA', () => {
    const view = renderPicker({
      from: berlin(2026, 3, 9, 8, 45),
      to: berlin(2026, 3, 10, 9, 0)
    })
    const button = triggerButton(view)
    expect(button.getAttribute('type')).toBe('button')
    expect(button.getAttribute('aria-haspopup')).toBe('dialog')
    expect(button.getAttribute('aria-expanded')).toBe('false')

    const summary = button.textContent ?? ''
    expect(summary).toContain('2026-03-09')
    expect(summary).toContain('08:45')
    expect(summary).toContain('2026-03-10')
    expect(summary).toContain('09:00')
  })

  test('clicking the trigger opens the dialog', async () => {
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 45), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)
    expect(view.currentOpen()).toBe(true)
    expect(triggerButton(view).getAttribute('aria-expanded')).toBe('true')
    expect(view.getByRole('dialog')).toBeInTheDocument()
  })

  test('a disabled trigger does not open', async () => {
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 45), to: berlin(2026, 3, 10, 9, 0) },
      { disabled: true }
    )
    expect(triggerButton(view)).toBeDisabled()
    await openFlyout(view)
    expect(view.currentOpen()).toBe(false)
  })
})

describe('CmkTimeRangePicker — Apply guard', () => {
  test('both endpoints set enables Apply', async () => {
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 45), to: berlin(2026, 3, 10, 9, 0) },
      { nullable: false }
    )
    await openFlyout(view)
    expect(applyButton(view)).toBeEnabled()
  })

  test('nullable with both endpoints empty enables Apply', async () => {
    const view = renderPicker(null, { nullable: true })
    await openFlyout(view)
    expect(applyButton(view)).toBeEnabled()
  })

  test('a half-empty range (only From set) disables Apply', async () => {
    const view = renderPicker(null, { nullable: true })
    await openFlyout(view)
    await setDate(view, 'From', 2026, 3, 9)
    expect(applyButton(view)).toBeDisabled()
    // The reason is announced to assistive tech via a visually-hidden polite live region.
    expect(view.getByText('Enter a complete start and end')).toBeInTheDocument()
  })

  test('date-only endpoints keep Apply disabled until both times are set', async () => {
    const view = renderPicker(null, { nullable: false })
    await openFlyout(view)
    await setDate(view, 'From', 2026, 3, 9)
    await setDate(view, 'To', 2026, 3, 10)
    expect(applyButton(view)).toBeDisabled()

    await setTime(view, 'From', 8, 0)
    expect(applyButton(view)).toBeDisabled()

    await setTime(view, 'To', 9, 0)
    expect(applyButton(view)).toBeEnabled()
  })
})

describe('CmkTimeRangePicker — ordering', () => {
  // A committed range is always ordered (from <= to), regardless of the path that triggered it.
  const orderedInstants = (range: DateTimeRange): boolean => range.from.compare(range.to) <= 0

  test('applying an inverted range orders it', async () => {
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)
    await setDate(view, 'From', 2026, 3, 15)
    await setDate(view, 'To', 2026, 3, 12)

    await fireEvent.click(applyButton(view))
    expect(orderedInstants(lastValue(view.updates)!)).toBe(true)
  })

  test('pressing Enter in a field orders the range and closes', async () => {
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)
    await setDate(view, 'From', 2026, 3, 15)
    await setDate(view, 'To', 2026, 3, 12)

    const fromDay = within(view.getByRole('group', { name: 'From date' })).getByRole('spinbutton', {
      name: 'Day'
    })
    await fireEvent.keyDown(fromDay, { key: 'Enter' })
    await nextTick()

    expect(orderedInstants(lastValue(view.updates)!)).toBe(true)
    expect(view.currentOpen()).toBe(false)
  })

  test('moving focus from the inputs to the calendar swaps an inverted draft', async () => {
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)
    await setDate(view, 'From', 2026, 3, 15)
    await setDate(view, 'To', 2026, 3, 12)

    // Focus leaves the inputs container but stays inside the flyout (lands on a calendar day), so
    // the range is reordered without dismissing the flyout.
    const inputs = view
      .getByRole('group', { name: 'From date' })
      .closest<HTMLElement>('.cmk-time-range-picker__inputs')!
    const calendarDay = view.container.querySelector<HTMLElement>('[data-date]')!
    inputs.dispatchEvent(new FocusEvent('focusout', { relatedTarget: calendarDay, bubbles: true }))
    await nextTick()

    expect(view.currentOpen()).toBe(true)
    // The endpoints are swapped so the earlier date is now From.
    expect(shownDay(view, 'From')).toBe('12')
    expect(shownDay(view, 'To')).toBe('15')
    // The swap is announced to assistive tech, naming both reordered endpoints. (The dates are
    // locale-formatted, so assert the stable template structure only.)
    expect(await view.findByText(/^Range reordered: start .+, end .+$/)).toBeInTheDocument()
  })

  test('the inputs form a labeled "Time range" group and the footer zone is not double-spoken', async () => {
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)

    // The From/To rows are grouped so assistive tech is oriented on entry.
    expect(view.getByRole('group', { name: 'Time range' })).toBeInTheDocument()

    // The TimeZoneTag's hidden text voices the zone, the visible elements should be hidden
    const zone = view.getByText('Timezone:').closest<HTMLElement>('.cmk-time-range-picker__zone')!
    expect(zone.querySelector('.cmk-tag')).toHaveAttribute('aria-hidden', 'true')
    expect(within(zone).getByText('Europe, Berlin')).toHaveAttribute('aria-hidden', 'true')
  })
})

describe('CmkTimeRangePicker — save mode applies from the inputs', () => {
  test('Enter in a From/To field runs the save handler, then commits and closes', async () => {
    const saveHandler = vi.fn(() => true)
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) },
      { saveMode: true, saveHandler }
    )
    await openFlyout(view)
    // Edit an endpoint so the commit actually writes (an unchanged range is an intentional no-op).
    await setDate(view, 'From', 2026, 3, 8)
    await fireEvent.click(view.getByRole('checkbox'))

    // Enter on the From day field is the same apply path as the footer "Save & apply".
    const fromDay = within(view.getByRole('group', { name: 'From date' })).getByRole('spinbutton', {
      name: 'Day'
    })
    await fireEvent.keyDown(fromDay, { key: 'Enter' })
    await nextTick()

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(lastValue(view.updates)!.from.toString()).toContain('2026-03-08')
    expect(view.currentOpen()).toBe(false)
  })

  test('a rejecting save handler keeps the flyout open and commits nothing', async () => {
    const saveHandler = vi.fn(() => false)
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) },
      { saveMode: true, saveHandler }
    )
    await openFlyout(view)
    await fireEvent.click(view.getByRole('checkbox'))

    const fromDay = within(view.getByRole('group', { name: 'From date' })).getByRole('spinbutton', {
      name: 'Day'
    })
    await fireEvent.keyDown(fromDay, { key: 'Enter' })
    await nextTick()

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(view.updates).toEqual([])
    expect(view.currentOpen()).toBe(true)
  })

  test('announces "Saving…" while the save handler is in flight', async () => {
    // Wiring guard: the picker forwards pendingSave so the footer can announce the in-flight save.
    const saveHandler = vi.fn(() => new Promise<boolean>(() => {}))
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) },
      { saveMode: true, saveHandler }
    )
    await openFlyout(view)
    await fireEvent.click(view.getByRole('checkbox'))
    await fireEvent.click(view.getByRole('button', { name: 'Save & apply' }))
    await nextTick()

    expect(saveHandler).toHaveBeenCalledOnce()
    expect(view.getByText('Saving…')).toBeInTheDocument()
  })
})

describe('CmkTimeRangePicker — server time readout', () => {
  test('with a server zone renders "<date>, <time>"', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-10T10:00:00Z'))
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) },
      { serverTimeZone: TZ_BERLIN }
    )
    await openFlyout(view)
    // 2026-06-10T10:00:00Z in Berlin (CEST, UTC+2) is 2026-06-10 12:00. ISO date + 24h time.
    expect(view.container.textContent).toContain('2026-06-10, 12:00')
  })

  test('without a server zone renders the em dash', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-10T10:00:00Z'))
    const view = renderPicker({ from: berlin(2026, 3, 9, 8, 0), to: berlin(2026, 3, 10, 9, 0) })
    await openFlyout(view)
    const serverBlock = view
      .getByText('Current server time:')
      .closest<HTMLElement>('.cmk-time-range-picker__zone')!
    expect(serverBlock.textContent).toContain('—')
  })
})

describe('CmkTimeRangePicker — trigger slot', () => {
  // Capture the trigger slot props on each render via a render-function slot.
  const slotCapture = () => {
    const captured: Record<string, unknown> = {}
    const slots = {
      trigger: (slotProps: Record<string, unknown>) => {
        Object.assign(captured, slotProps)
        const aria = (slotProps.aria ?? {}) as Record<string, unknown>
        return h('button', { type: 'button', 'data-testid': 'trigger', ...aria }, 'trigger')
      }
    }
    return { captured, slots }
  }

  test('exposes the decomposed endpoints and is display-only (no commit)', () => {
    const { captured, slots } = slotCapture()
    renderPicker({ from: berlin(2026, 3, 9, 8, 45), to: berlin(2026, 3, 10, 9, 0) }, {}, slots)

    const fields = captured.fields as RangeDraft
    expect(fields.from.date?.toString()).toBe('2026-03-09')
    expect(fields.from.time).toEqual({ hour: 8, minute: 45 })
    expect(fields.to.date?.toString()).toBe('2026-03-10')
    expect(fields.to.time).toEqual({ hour: 9, minute: 0 })

    // Receives the documented props, and crucially NOT `commit`.
    expect(captured).toHaveProperty('open')
    expect(captured).toHaveProperty('aria')
    expect(captured).toHaveProperty('disabled')
    expect(captured).toHaveProperty('settings')
    expect(captured).not.toHaveProperty('commit')
  })

  test('fields are null for a null model', () => {
    const { captured, slots } = slotCapture()
    renderPicker(null, { nullable: true }, slots)
    expect(captured.fields).toEqual({
      from: { date: null, time: null },
      to: { date: null, time: null }
    })
  })

  test('fields reflect live staged edits and revert on Escape', async () => {
    const { captured, slots } = slotCapture()
    const view = renderPicker(
      { from: berlin(2026, 3, 9, 8, 45), to: berlin(2026, 3, 10, 9, 0) },
      {},
      slots
    )
    await fireEvent.click(screen.getByTestId('trigger'))
    await nextTick()

    // Edit the From date inside the open flyout; the slot's live fields follow.
    await setDate(view, 'From', 2026, 3, 11)
    expect((captured.fields as RangeDraft).from.date?.toString()).toBe('2026-03-11')

    // Dismiss via Escape (no apply) → the draft reverts to the committed range.
    await fireEvent.keyDown(view.getByRole('dialog'), { key: 'Escape' })
    await nextTick()
    expect((captured.fields as RangeDraft).from.date?.toString()).toBe('2026-03-09')
  })
})
