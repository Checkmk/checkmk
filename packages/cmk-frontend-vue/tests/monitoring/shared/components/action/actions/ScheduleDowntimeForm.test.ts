/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { parseAbsolute, toZoned } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it, test } from 'vitest'

import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues,
  downtimeWindow,
  isScheduleDowntimeValid,
  untilPresetEnd
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'

function mountForm(overrides: Partial<ScheduleDowntimeFormValues> = {}) {
  const modelValue: ScheduleDowntimeFormValues = {
    ...defaultScheduleDowntimeValues(),
    ...overrides
  }
  return render(ScheduleDowntimeForm, { props: { modelValue } })
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

test('a duration preset explains itself as a duration', () => {
  mountForm({ comment: 'maintenance', selection: '4h' })

  expect(
    screen.getByText('Scheduled downtime, starting now with a duration of 4 hours.')
  ).toBeInTheDocument()
})

test('an until preset explains itself with the end date', () => {
  mountForm({ comment: 'maintenance', selection: 'today' })

  expect(screen.getByText(/Scheduled downtime, starting now and ending on/)).toBeInTheDocument()
})

describe('isScheduleDowntimeValid', () => {
  it('requires a non-empty comment', () => {
    expect(isScheduleDowntimeValid({ ...defaultScheduleDowntimeValues(), comment: '' })).toBe(false)
    expect(isScheduleDowntimeValid({ ...defaultScheduleDowntimeValues(), comment: 'x' })).toBe(true)
  })

  it('rejects a zero ad hoc duration', () => {
    expect(
      isScheduleDowntimeValid({
        ...defaultScheduleDowntimeValues(),
        comment: 'x',
        selection: 'adhoc',
        adhocHours: 0,
        adhocMinutes: 0
      })
    ).toBe(false)
  })
})

describe('downtimeWindow', () => {
  it('spans the preset duration for a preset selection', () => {
    const window = downtimeWindow({ ...defaultScheduleDowntimeValues(), selection: '4h' })

    expect(window).not.toBeNull()
    const spanMs = new Date(window!.end).getTime() - new Date(window!.start).getTime()
    expect(spanMs).toBe(4 * 60 * 60_000)
  })

  it('returns null for an empty ad hoc duration', () => {
    const window = downtimeWindow({
      ...defaultScheduleDowntimeValues(),
      selection: 'adhoc',
      adhocHours: 0,
      adhocMinutes: 0
    })

    expect(window).toBeNull()
  })

  it.each(['today', 'week', 'month', 'year'] as const)(
    'ends on a later calendar boundary for the %s preset',
    (selection) => {
      const window = downtimeWindow({ ...defaultScheduleDowntimeValues(), selection })

      expect(window).not.toBeNull()
      expect(new Date(window!.end).getTime()).toBeGreaterThan(new Date(window!.start).getTime())
    }
  )
})

describe('untilPresetEnd', () => {
  const start = toZoned(parseAbsolute('2026-08-04T10:30:00Z', 'UTC'), 'UTC')

  it('ends at the start of the next day for today', () => {
    expect(untilPresetEnd('today', start).toString()).toBe('2026-08-05T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the day after the coming Sunday for the week', () => {
    expect(untilPresetEnd('week', start).toString()).toBe('2026-08-10T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the next month', () => {
    expect(untilPresetEnd('month', start).toString()).toBe('2026-09-01T00:00:00+00:00[UTC]')
  })

  it('ends at the start of the next year', () => {
    expect(untilPresetEnd('year', start).toString()).toBe('2027-01-01T00:00:00+00:00[UTC]')
  })
})
