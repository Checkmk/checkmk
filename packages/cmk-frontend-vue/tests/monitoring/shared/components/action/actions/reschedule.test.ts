/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type { RescheduleResult } from '@/monitoring/shared/api/actions/reschedule'
import {
  CHECK_POLL_INTERVAL_MS,
  createRescheduleAction
} from '@/monitoring/shared/components/action/actions/reschedule'

const ERROR_HEADING = untranslated('Could not reschedule the checks for the selected hosts')

const SCHEDULED_AT = 1_800_000_000

const RESCHEDULED: RescheduleResult = {
  rescheduled: 1,
  scheduledAt: SCHEDULED_AT,
  waitTimeoutSeconds: 3
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

function action(
  reschedule: () => Promise<RescheduleResult>,
  lastCheck: () => Promise<number | null> = async () => null
) {
  return createRescheduleAction<string>({
    reschedule,
    lastCheck,
    checkRan: (host) => untranslated(`The check of ${host} has run`),
    errorHeading: ERROR_HEADING
  })
}

/** The last checks the core reports, one per look, repeating the last one. */
function lastChecks(...answers: (number | null | Error)[]): () => Promise<number | null> {
  let looks = 0
  return async () => {
    const answer = answers[Math.min(looks++, answers.length - 1)]!
    if (answer instanceof Error) {
      throw answer
    }
    return answer
  }
}

test('a refused reschedule comes back as an error, not as a confirmation', async () => {
  const built = action(async () => {
    throw new CmkApiError('Forbidden', null, '', 403)
  })

  const feedback = await built.perform(['host-1'], built.defaultValues())

  expect(feedback).toEqual({
    variant: 'error',
    heading: ERROR_HEADING,
    message: 'Retry the command. If it keeps failing, check whether the site is running.'
  })
})

test('rescheduling one object confirms only once its check has run', async () => {
  const built = action(
    async () => RESCHEDULED,
    lastChecks(SCHEDULED_AT - 60, SCHEDULED_AT - 60, SCHEDULED_AT + 1)
  )

  const feedback = built.perform(['host-1'], built.defaultValues())
  await vi.advanceTimersByTimeAsync(3 * CHECK_POLL_INTERVAL_MS)

  expect(await feedback).toEqual({ variant: 'success', message: 'The check of host-1 has run' })
})

test('rescheduling one object warns when its check has not run within the timeout', async () => {
  const built = action(async () => RESCHEDULED, lastChecks(SCHEDULED_AT - 60))

  const feedback = built.perform(['host-1'], built.defaultValues())
  await vi.advanceTimersByTimeAsync(4 * CHECK_POLL_INTERVAL_MS)

  expect(await feedback).toEqual({
    variant: 'warning',
    message:
      'The check did not run within 3 seconds. It will still run as scheduled, and its result will show once the page refreshes.'
  })
})

test('a failed look at the check does not end the wait', async () => {
  const built = action(async () => RESCHEDULED, lastChecks(new Error('Bad gateway'), SCHEDULED_AT))

  const feedback = built.perform(['host-1'], built.defaultValues())
  await vi.advanceTimersByTimeAsync(2 * CHECK_POLL_INTERVAL_MS)

  expect(await feedback).toEqual({ variant: 'success', message: 'The check of host-1 has run' })
})

test('rescheduling several objects confirms without waiting for their checks', async () => {
  const built = action(async () => ({ ...RESCHEDULED, rescheduled: 2 }))

  const feedback = await built.perform(['host-1', 'host-2'], built.defaultValues())

  expect(feedback).toEqual({ variant: 'success', message: 'Rescheduled 2 checks' })
})

test('a check that can no longer be looked at ends the wait at once', async () => {
  const gone = new CmkApiError('Not Found', null, '', 404)
  const built = action(async () => RESCHEDULED, lastChecks(gone))

  const feedback = built.perform(['host-1'], built.defaultValues())
  await vi.advanceTimersByTimeAsync(CHECK_POLL_INTERVAL_MS)

  expect(await feedback).toEqual({
    variant: 'warning',
    message:
      'The check was rescheduled, but its result could not be read. It will show once the page refreshes.'
  })
})

test('an aborted wait looks at the check no more', async () => {
  let looks = 0
  const built = action(
    async () => RESCHEDULED,
    async () => {
      looks += 1
      return SCHEDULED_AT - 60
    }
  )
  const controller = new AbortController()

  const feedback = built.perform(['host-1'], built.defaultValues(), controller.signal)
  await vi.advanceTimersByTimeAsync(CHECK_POLL_INTERVAL_MS)
  controller.abort()
  await vi.advanceTimersByTimeAsync(3 * CHECK_POLL_INTERVAL_MS)
  await feedback

  expect(looks).toBe(1)
})

test('an abort while the check is looked at ends the wait at once', async () => {
  const controller = new AbortController()
  const built = action(
    async () => RESCHEDULED,
    async () => {
      controller.abort()
      return SCHEDULED_AT - 60
    }
  )
  let outcome: unknown
  void built
    .perform(['host-1'], built.defaultValues(), controller.signal)
    .then((feedback) => (outcome = feedback))

  await vi.advanceTimersByTimeAsync(CHECK_POLL_INTERVAL_MS)

  expect(outcome).toEqual({
    variant: 'warning',
    message:
      'The check was rescheduled, but its result could not be read. It will show once the page refreshes.'
  })
})
