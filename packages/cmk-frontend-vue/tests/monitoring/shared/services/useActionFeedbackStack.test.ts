/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { expect, test, vi } from 'vitest'
import { effectScope } from 'vue'

import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { useActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'

const WAITING = untranslated('Waiting for the check of web-01 to finish')
const RAN: ActionOutcome = { variant: 'success', message: untranslated('The check has run') }
const FAILED: ActionOutcome = { variant: 'error', message: untranslated('Could not reschedule') }

/** An action that runs until the test settles it. */
function running(): {
  run: () => Promise<ActionOutcome>
  settle: (outcome: ActionOutcome) => void
} {
  let settle: (outcome: ActionOutcome) => void = () => {}
  const outcome = new Promise<ActionOutcome>((resolve) => (settle = resolve))
  return { run: () => outcome, settle }
}

/** An action that runs until no one waits for it any more, handing the test its signal. */
function stoppable(): {
  run: (signal?: AbortSignal) => Promise<ActionOutcome>
  signal: () => AbortSignal | undefined
} {
  let given: AbortSignal | undefined
  return {
    run: (signal) => {
      given = signal
      return new Promise(() => {})
    },
    signal: () => given
  }
}

function shown(stack: ReturnType<typeof useActionFeedbackStack>) {
  return stack.items.value.map((item) => item.feedback)
}

test('tells an action runs while it does', () => {
  const stack = useActionFeedbackStack()

  void stack.track({ pending: WAITING, perform: running().run })

  expect(shown(stack)).toEqual([{ variant: 'loading', message: WAITING }])
})

test('turns the alert of a running action into its outcome once it settles', async () => {
  const stack = useActionFeedbackStack()
  const action = running()
  const tracked = stack.track({ pending: WAITING, perform: action.run })

  action.settle(RAN)
  await tracked

  expect(shown(stack)).toEqual([RAN])
})

test('tells each action still running in an alert of its own', () => {
  const stack = useActionFeedbackStack()

  void stack.track({ pending: WAITING, perform: running().run })
  void stack.track({ pending: WAITING, perform: running().run })

  expect(shown(stack)).toHaveLength(2)
})

test('drops the outcomes told before once another action is told about', () => {
  const stack = useActionFeedbackStack()
  stack.show(FAILED)

  stack.show(RAN)

  expect(shown(stack)).toEqual([RAN])
})

test('drops the outcomes told before once another action starts running', () => {
  const stack = useActionFeedbackStack()
  stack.show(FAILED)

  void stack.track({ pending: WAITING, perform: running().run })

  expect(shown(stack)).toEqual([{ variant: 'loading', message: WAITING }])
})

test('takes the outcomes away, keeping the alerts of actions still running', () => {
  const stack = useActionFeedbackStack()
  void stack.track({ pending: WAITING, perform: running().run })
  stack.show(FAILED)

  stack.dropOutcomes()

  expect(shown(stack)).toEqual([{ variant: 'loading', message: WAITING }])
})

test('keeps the alerts of actions still running when another action is told about', () => {
  const stack = useActionFeedbackStack()
  void stack.track({ pending: WAITING, perform: running().run })

  stack.show(FAILED)

  expect(shown(stack)).toEqual([{ variant: 'loading', message: WAITING }, FAILED])
})

test('drops the outcomes told before once a running action settles', async () => {
  const stack = useActionFeedbackStack()
  const action = running()
  const tracked = stack.track({ pending: WAITING, perform: action.run })
  stack.show(FAILED)

  action.settle(RAN)
  await tracked

  expect(shown(stack)).toEqual([RAN])
})

test('tells nothing while an action without a pending text runs', () => {
  const stack = useActionFeedbackStack()

  void stack.track({ pending: undefined, perform: running().run })

  expect(shown(stack)).toEqual([])
})

test('tells the command failed when its action fails rather than telling how it went', async () => {
  const stack = useActionFeedbackStack()

  vi.spyOn(console, 'error').mockImplementation(() => {})

  await stack.track({ pending: WAITING, perform: () => Promise.reject(new Error('offline')) })

  expect(shown(stack).map((feedback) => feedback.variant)).toEqual(['error'])
})

test('an alert cleared away while its action runs stays away once it settles', async () => {
  const stack = useActionFeedbackStack()
  const action = running()
  const tracked = stack.track({ pending: WAITING, perform: action.run })
  stack.clear()

  action.settle(RAN)
  await tracked

  expect(shown(stack)).toEqual([])
})

test('takes away an alert its user has closed', () => {
  const stack = useActionFeedbackStack()
  stack.show(RAN)

  stack.dismiss(stack.items.value[0]!.id)

  expect(shown(stack)).toEqual([])
})

test('does not run an action again while the one under its key still runs', () => {
  const stack = useActionFeedbackStack()
  const again = vi.fn(running().run)
  void stack.track({ pending: WAITING, perform: running().run, key: 'reschedule@web-01' })

  void stack.track({ pending: WAITING, perform: again, key: 'reschedule@web-01' })

  expect(again).not.toHaveBeenCalled()
  expect(shown(stack)).toEqual([{ variant: 'loading', message: WAITING }])
})

test('does not run an action telling nothing while it runs again while the one under its key runs', () => {
  const stack = useActionFeedbackStack()
  const again = vi.fn(running().run)
  void stack.track({ pending: undefined, perform: running().run, key: 'acknowledge@web-01' })

  void stack.track({ pending: undefined, perform: again, key: 'acknowledge@web-01' })

  expect(again).not.toHaveBeenCalled()
})

test('runs an action again once the one under its key has settled', async () => {
  const stack = useActionFeedbackStack()
  const first = running()
  const done = stack.track({ pending: WAITING, perform: first.run, key: 'reschedule@web-01' })
  first.settle(RAN)
  await done
  const again = vi.fn(running().run)

  void stack.track({ pending: WAITING, perform: again, key: 'reschedule@web-01' })

  expect(again).toHaveBeenCalledOnce()
})

test('runs an action again once the alert of the one under its key is cleared away', () => {
  const stack = useActionFeedbackStack()
  void stack.track({ pending: WAITING, perform: running().run, key: 'reschedule@web-01' })
  stack.clear()
  const again = vi.fn(running().run)

  void stack.track({ pending: WAITING, perform: again, key: 'reschedule@web-01' })

  expect(again).toHaveBeenCalledOnce()
})

test('stops an action once its alert is cleared away', () => {
  const stack = useActionFeedbackStack()
  const action = stoppable()
  void stack.track({ pending: WAITING, perform: action.run })

  stack.clear()

  expect(action.signal()?.aborted).toBe(true)
})

test('stops an action once its alert is taken away', () => {
  const stack = useActionFeedbackStack()
  const action = stoppable()
  void stack.track({ pending: WAITING, perform: action.run })

  stack.dismiss(stack.items.value[0]!.id)

  expect(action.signal()?.aborted).toBe(true)
})

test('stops the actions once the page showing the alerts is gone', () => {
  const page = effectScope()
  const stack = page.run(() => useActionFeedbackStack())!
  const action = stoppable()
  void stack.track({ pending: WAITING, perform: action.run })

  page.stop()

  expect(action.signal()?.aborted).toBe(true)
})

test('keeps an action running while its alert is on show', () => {
  const stack = useActionFeedbackStack()
  const action = stoppable()
  void stack.track({ pending: WAITING, perform: action.run })

  stack.show(RAN)

  expect(action.signal()?.aborted).toBe(false)
})

test('hands on no outcome of an action no one waits for any more', async () => {
  const stack = useActionFeedbackStack()
  const action = running()
  const tracked = stack.track({ pending: undefined, perform: action.run })
  stack.clear()

  action.settle(FAILED)

  await expect(tracked).resolves.toBeNull()
  expect(shown(stack)).toEqual([])
})

test('tells which keys actions run under while they do', () => {
  const stack = useActionFeedbackStack()

  void stack.track({ pending: WAITING, perform: running().run, key: 'reschedule@web-01' })

  expect([...stack.runningKeys.value]).toEqual(['reschedule@web-01'])
})

test('tells no key an action runs under once it has settled', async () => {
  const stack = useActionFeedbackStack()
  const action = running()
  const tracked = stack.track({ pending: WAITING, perform: action.run, key: 'reschedule@web-01' })

  action.settle(RAN)
  await tracked

  expect([...stack.runningKeys.value]).toEqual([])
})

test('tells no key an action runs under once it is stopped', () => {
  const stack = useActionFeedbackStack()
  void stack.track({ pending: WAITING, perform: running().run, key: 'reschedule@web-01' })

  stack.clear()

  expect([...stack.runningKeys.value]).toEqual([])
})
