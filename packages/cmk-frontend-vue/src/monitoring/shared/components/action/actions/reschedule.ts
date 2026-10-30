/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { RescheduleApi, type RescheduleResult } from '@/monitoring/shared/api/actions/reschedule'

import type { ActionOutcome, MonitoringAction } from '../types'
import RescheduleForm, { type RescheduleValues } from './RescheduleForm.vue'
import { commandFailed } from './feedback'

export const RESCHEDULE_ACTION_ID = 'reschedule'

const DEFAULT_SPREAD_MINUTES = 5

/** How often to ask whether a rescheduled check has run. */
export const CHECK_POLL_INTERVAL_MS = 1000

export interface RescheduleKindConfig<Target> {
  /** Perform the API call for the selected targets. */
  reschedule(
    api: RescheduleApi,
    targets: Target[],
    spreadMinutes: number
  ): Promise<RescheduleResult>
  /** When the check of the target last ran, null if it never has. */
  lastCheck(target: Target): Promise<number | null>
  /** Tells that the check of the target has run, naming what ran. */
  checkRan(target: Target): TranslatedString
  errorHeading: TranslatedString
}

/** Wait for `ms`, or until the signal aborts, whichever comes first. */
function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    // An abort that came before the wait fires no event for it to hear.
    if (signal?.aborted) {
      resolve()
      return
    }
    const timer = setTimeout(done, ms)
    signal?.addEventListener('abort', done, { once: true })
    function done(): void {
      clearTimeout(timer)
      signal?.removeEventListener('abort', done)
      resolve()
    }
  })
}

/** Whether the check has run, has not run yet, or can no longer be looked at. */
type CheckLook = 'run' | 'pending' | 'unreadable'

/**
 * Shared reschedule flow for hosts and services. The wording is the same for both, because the
 * command reschedules checks either way; only the API calls, the naming of what ran and the error
 * heading differ.
 *
 * Rescheduling one target waits for its check to run, as the legacy views did, so that what
 * follows - the success message and the reload of the page - shows the check's result. Several
 * selected services may come down to one target: those that are byproducts of a host's
 * "Check_MK" service reschedule that service, once. A check that takes longer than the configured
 * timeout is left to run; the user is told so and nothing reloads. Rescheduling several targets
 * spreads their checks out, so it does not wait.
 *
 * The wait ends early once its signal aborts, as no one is left to tell, or once the object can
 * no longer be looked at, e.g. it has been removed.
 */
export function createRescheduleAction<Target>(
  config: RescheduleKindConfig<Target>
): MonitoringAction<RescheduleValues, Target> {
  const { _t, _tn } = usei18n()
  const api = new RescheduleApi()

  async function look(target: Target, since: number): Promise<CheckLook> {
    try {
      const lastCheck = await config.lastCheck(target)
      return lastCheck !== null && lastCheck >= since ? 'run' : 'pending'
    } catch (error) {
      // An object that is gone or out of sight stays so. Anything else - a site that does not
      // answer, a server error - may pass: keep asking until the timeout.
      const refused =
        error instanceof CmkApiError && error.statusCode >= 400 && error.statusCode < 500
      return refused ? 'unreadable' : 'pending'
    }
  }

  function resultUnknown(): ActionOutcome {
    return {
      variant: 'warning',
      message: _t(
        'The check was rescheduled, but its result could not be read. It will show once the page refreshes.'
      )
    }
  }

  async function waitForCheck(
    target: Target,
    result: RescheduleResult,
    signal: AbortSignal | undefined
  ): Promise<ActionOutcome> {
    const deadline = Date.now() + result.waitTimeoutSeconds * 1000
    while (Date.now() < deadline) {
      await delay(CHECK_POLL_INTERVAL_MS, signal)
      if (signal?.aborted) {
        return resultUnknown()
      }
      const seen = await look(target, result.scheduledAt)
      if (seen === 'run') {
        return { variant: 'success', message: config.checkRan(target) }
      }
      if (seen === 'unreadable') {
        return resultUnknown()
      }
    }
    const seconds = result.waitTimeoutSeconds
    return {
      variant: 'warning',
      message: _tn(
        'The check did not run within %{seconds} second. It will still run as scheduled, and its result will show once the page refreshes.',
        'The check did not run within %{seconds} seconds. It will still run as scheduled, and its result will show once the page refreshes.',
        seconds,
        { seconds: String(seconds) }
      )
    }
  }

  return {
    id: RESCHEDULE_ACTION_ID,
    title: _t('Reschedule active checks'),
    submitLabel: _t('Reschedule checks'),
    description: [
      _t('Execution will be spread across custom time period to avoid network overload.')
    ],
    form: RescheduleForm,
    defaultValues: () => ({ spreadMinutes: DEFAULT_SPREAD_MINUTES }),
    perform: async (targets: Target[], values: RescheduleValues, signal?: AbortSignal) => {
      let result: RescheduleResult
      try {
        result = await config.reschedule(api, targets, values.spreadMinutes ?? 0)
      } catch {
        return commandFailed(config.errorHeading)
      }
      const [only] = targets
      if (targets.length === 1 && only !== undefined) {
        return waitForCheck(only, result, signal)
      }
      const count = result.rescheduled
      return {
        variant: 'success',
        message: _tn('Rescheduled %{count} check', 'Rescheduled %{count} checks', count, {
          count
        })
      }
    }
  }
}
