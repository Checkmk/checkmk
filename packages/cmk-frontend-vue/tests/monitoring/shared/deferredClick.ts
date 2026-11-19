/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { onTestFinished, vi } from 'vitest'

import { DOUBLE_CLICK_MS } from '@/monitoring/shared/plainClick'

/**
 * A user clicking on a fake `setTimeout`, so `pastDoubleClick` skips the wait for a second click
 * instead of sleeping. It still runs, so other timeouts of the page fire as usual; `Date` and the
 * other timers stay real.
 */
export function userOnFakeClock(): UserEvent {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'], shouldAdvanceTime: true })
  onTestFinished(() => {
    vi.useRealTimers()
  })
  return userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
}

export async function pastDoubleClick(): Promise<void> {
  await vi.advanceTimersByTimeAsync(DOUBLE_CLICK_MS)
}

/** Marks the first letters of `element`'s text by dragging over them, ending in a click. */
export async function markText(user: UserEvent, element: Element): Promise<void> {
  await user.pointer([
    { keys: '[MouseLeft>]', target: element, offset: 0 },
    { offset: 5 },
    { keys: '[/MouseLeft]' }
  ])
}
