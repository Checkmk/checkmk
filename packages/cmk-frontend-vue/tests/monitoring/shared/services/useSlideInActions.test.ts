/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, nextTick, ref } from 'vue'

import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { ActionOutcome, MonitoringAction } from '@/monitoring/shared/components/action/types'
import { useSlideInActions } from '@/monitoring/shared/services/useSlideInActions'

let scope: EffectScope | null = null

const AWAITING_CHECK = untranslated('Waiting for the check of host-1 to finish')

afterEach(() => {
  scope?.stop()
  scope = null
})

/**
 * A reschedule that waits until the test settles it or breaks it off, handing the test the signal
 * it was given.
 */
function slowReschedule() {
  const run: {
    settle: (outcome: ActionOutcome) => void
    breakOff: (error: Error) => void
    signal?: AbortSignal | undefined
  } = {
    settle: () => {},
    breakOff: () => {}
  }
  const action: MonitoringAction<unknown, string> = {
    id: RESCHEDULE_ACTION_ID,
    title: untranslated('Reschedule'),
    submitLabel: untranslated('Reschedule'),
    defaultValues: () => ({}),
    pending: () => AWAITING_CHECK,
    perform: (_targets, _values, signal) => {
      run.signal = signal
      return new Promise((resolve, reject) => {
        run.settle = resolve
        run.breakOff = reject
      })
    }
  }
  return { action, run }
}

const ACKNOWLEDGE_ID = 'acknowledge'
const ACKNOWLEDGED: ActionOutcome = { variant: 'success', message: untranslated('Acknowledged') }

/** An action that asks for input, so that picking it opens its form. */
const acknowledge: MonitoringAction<unknown, string> = {
  id: ACKNOWLEDGE_ID,
  title: untranslated('Acknowledge'),
  submitLabel: untranslated('Acknowledge'),
  defaultValues: () => ({}),
  perform: () => Promise.resolve(ACKNOWLEDGED)
}

function shown(slideIn: ReturnType<typeof slideInOn>) {
  return slideIn.alerts.items.value.map((item) => item.feedback)
}

function slideInOn(subject: { value: string }, action: MonitoringAction<unknown, string>) {
  scope = effectScope()
  return scope.run(() =>
    useSlideInActions<string>(
      () => ({ [RESCHEDULE_ACTION_ID]: action, [ACKNOWLEDGE_ID]: acknowledge }),
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

  expect(shown(slideIn)).toEqual([])
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

test('tells an action performed right away runs while it does', () => {
  const { action } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)

  void slideIn.openAction(RESCHEDULE_ACTION_ID)

  expect(shown(slideIn)).toEqual([{ variant: 'loading', message: AWAITING_CHECK }])
})

test('tells how an action performed right away went once it settles', async () => {
  const { action, run } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  const running = slideIn.openAction(RESCHEDULE_ACTION_ID)
  const ran: ActionOutcome = { variant: 'success', message: untranslated('The check has run') }

  run.settle(ran)
  await running

  expect(shown(slideIn)).toEqual([ran])
})

test('tells the command failed once an action performed right away breaks off', async () => {
  const { action, run } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  const running = slideIn.openAction(RESCHEDULE_ACTION_ID)
  vi.spyOn(console, 'error').mockImplementation(() => {})

  run.breakOff(new Error('The connection broke off'))
  await running

  expect(shown(slideIn).map((feedback) => feedback.variant)).toEqual(['error'])
})

test('performs an action picked again while it runs only once', async () => {
  const { action } = slowReschedule()
  const perform = vi.spyOn(action, 'perform')
  const slideIn = slideInOn(ref('host-1'), action)
  void slideIn.openAction(RESCHEDULE_ACTION_ID)

  await slideIn.openAction(RESCHEDULE_ACTION_ID)

  expect(perform).toHaveBeenCalledOnce()
  expect(shown(slideIn)).toEqual([{ variant: 'loading', message: AWAITING_CHECK }])
})

test('tells how a form went next to an action performed right away that still runs', async () => {
  const { action } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  void slideIn.openAction(RESCHEDULE_ACTION_ID)
  await slideIn.openAction(ACKNOWLEDGE_ID)

  slideIn.applyFeedback(ACKNOWLEDGED)

  expect(shown(slideIn)).toEqual([{ variant: 'loading', message: AWAITING_CHECK }, ACKNOWLEDGED])
})

test('still tells an action performed right away runs once a form is opened', async () => {
  const { action } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  void slideIn.openAction(RESCHEDULE_ACTION_ID)

  await slideIn.openAction(ACKNOWLEDGE_ID)

  expect(shown(slideIn)).toEqual([{ variant: 'loading', message: AWAITING_CHECK }])
})

test('leaves a form opened while an action performed right away runs open once it settles', async () => {
  const { action, run } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  const running = slideIn.openAction(RESCHEDULE_ACTION_ID)
  await slideIn.openAction(ACKNOWLEDGE_ID)
  const ran: ActionOutcome = { variant: 'success', message: untranslated('The check has run') }

  run.settle(ran)
  await running

  expect(slideIn.activeActionId.value).toBe(ACKNOWLEDGE_ID)
  expect(shown(slideIn)).toEqual([ran])
})

test('keeps an action performed right away pulsing while another one settles', async () => {
  const { action } = slowReschedule()
  const slideIn = slideInOn(ref('host-1'), action)
  void slideIn.openAction(RESCHEDULE_ACTION_ID)

  await slideIn.perform(ACKNOWLEDGE_ID, ['host-1'])

  expect([...slideIn.runningActionIds.value]).toEqual([RESCHEDULE_ACTION_ID])
})
