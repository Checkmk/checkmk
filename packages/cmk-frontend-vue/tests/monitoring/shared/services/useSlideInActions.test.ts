/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach, expect, test } from 'vitest'
import { type EffectScope, effectScope, nextTick, ref } from 'vue'

import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { ActionOutcome, MonitoringAction } from '@/monitoring/shared/components/action/types'
import { useSlideInActions } from '@/monitoring/shared/services/useSlideInActions'

let scope: EffectScope | null = null

afterEach(() => {
  scope?.stop()
  scope = null
})

/** A reschedule that waits until the test settles it, handing the test the signal it was given. */
function slowReschedule() {
  const run: { settle: (outcome: ActionOutcome) => void; signal?: AbortSignal | undefined } = {
    settle: () => {}
  }
  const action: MonitoringAction<unknown, string> = {
    id: RESCHEDULE_ACTION_ID,
    title: untranslated('Reschedule'),
    submitLabel: untranslated('Reschedule'),
    defaultValues: () => ({}),
    perform: (_targets, _values, signal) => {
      run.signal = signal
      return new Promise((resolve) => (run.settle = resolve))
    }
  }
  return { action, run }
}

function slideInOn(subject: { value: string }, action: MonitoringAction<unknown, string>) {
  scope = effectScope()
  return scope.run(() =>
    useSlideInActions<string>(
      () => ({ [RESCHEDULE_ACTION_ID]: action }),
      () => [subject.value],
      () => subject.value,
      () => {}
    )
  )!
}

test('drops the outcome of an action run for the object on show before another was', async () => {
  const subject = ref('host-1')
  const { action, run } = slowReschedule()
  const slideIn = slideInOn(subject, action)
  const running = slideIn.openAction(RESCHEDULE_ACTION_ID)
  subject.value = 'host-2'
  await nextTick()

  run.settle({ variant: 'success', message: untranslated('The check of host-1 has run') })
  await running

  expect(slideIn.feedback.value).toBeNull()
})

test('stops waiting for an action once another object is on show', async () => {
  const subject = ref('host-1')
  const { action, run } = slowReschedule()
  const slideIn = slideInOn(subject, action)
  void slideIn.openAction(RESCHEDULE_ACTION_ID)

  subject.value = 'host-2'
  await nextTick()

  expect(run.signal?.aborted).toBe(true)
})
