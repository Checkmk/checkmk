/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, computed, getCurrentScope, onScopeDispose, reactive, ref } from 'vue'

import { commandFailed } from '@/monitoring/shared/components/action/actions/feedback'
import type { ActionRun } from '@/monitoring/shared/components/action/run'
import type {
  ActionFeedbackEntry,
  ActionOutcome
} from '@/monitoring/shared/components/action/types'

export interface FeedbackStackItem {
  id: number
  feedback: ActionFeedbackEntry
}

export interface ActionFeedbackStack {
  /** The alerts on show, in the order they appeared. */
  items: ComputedRef<readonly FeedbackStackItem[]>
  /** The keys of the actions still running, e.g. to tell which of their buttons pulse. */
  runningKeys: ComputedRef<ReadonlySet<string>>
  /** Tells how an action went. */
  show: (outcome: ActionOutcome) => void
  /**
   * Runs an action, telling its `pending` text while it runs, if it has one, and how it went once
   * it has settled. An action that fails rather than telling how it went tells that the command
   * failed.
   *
   * The action is handed a signal that aborts once no one waits for it any more: its alert is
   * taken or cleared away, or the page showing the alerts is gone. Whatever it tells then is not
   * told, and no outcome is handed on.
   *
   * An action under the `key` of one still running, e.g. a reschedule picked again in the same row,
   * is not run again, and hands on no outcome: the one running tells how it goes. One stopped - its
   * alert taken or cleared away - no longer runs.
   */
  track: (run: ActionRun) => Promise<ActionOutcome | null>
  /** Takes the outcomes away, keeping the alerts of actions still running. */
  dropOutcomes: () => void
  /** Takes an alert away, e.g. once its user has closed it. */
  dismiss: (id: number) => void
  /** Takes every alert away, e.g. once the page shows something else. */
  clear: () => void
}

/**
 * The feedback alerts of a page that runs several actions at once, e.g. rescheduling the checks of
 * two rows, each waiting for its check: one alert per action still running, each turning into its
 * outcome in place once settled.
 *
 * An alert told - of an action told about, of one starting to run, or of one settled - drops the
 * outcomes told before, as the newest is the one that matters. An error cannot be closed, so they
 * would otherwise pile up. Alerts of actions still running stay.
 *
 * The page is gone with the scope that made the stack. One made outside of any, e.g. in a test,
 * never is.
 */
export function useActionFeedbackStack(): ActionFeedbackStack {
  const { _t } = usei18n()
  const items = ref<FeedbackStackItem[]>([])
  let nextId = 0
  // What stops each action still running, by the id of its alert.
  const running = new Map<number, AbortController>()
  // The action running under each key, by the id of its alert. One stopped no longer runs.
  const runningUnder = reactive(new Map<string, number>())

  function stopWaiting(ids: Iterable<number>): void {
    const stopped = new Set(ids)
    for (const id of stopped) {
      running.get(id)?.abort()
    }
    for (const [key, id] of [...runningUnder]) {
      if (stopped.has(id)) {
        runningUnder.delete(key)
      }
    }
  }

  if (getCurrentScope()) {
    onScopeDispose(() => stopWaiting(running.keys()))
  }

  const isRunning = (item: FeedbackStackItem) => item.feedback.variant === 'loading'

  function push(feedback: ActionFeedbackEntry, id: number = nextId++): void {
    items.value = [...items.value.filter(isRunning), { id, feedback }]
  }

  function show(outcome: ActionOutcome): void {
    push(outcome)
  }

  function settle(id: number, outcome: ActionOutcome | null): void {
    // An alert cleared away meanwhile stays away. One settled stays in place, not to jump about.
    if (!items.value.some((item) => item.id === id)) {
      return
    }
    items.value = items.value.flatMap((item) => {
      if (item.id === id) {
        return outcome ? [{ id, feedback: outcome }] : []
      }
      return outcome && !isRunning(item) ? [] : [item]
    })
  }

  async function track(run: ActionRun): Promise<ActionOutcome | null> {
    const { pending, key } = run
    if (key !== undefined && runningUnder.has(key)) {
      return null
    }
    const id = nextId++
    const waiting = new AbortController()
    running.set(id, waiting)
    if (key !== undefined) {
      runningUnder.set(key, id)
    }
    if (pending !== undefined) {
      push({ variant: 'loading', message: pending }, id)
    }
    let told: ActionOutcome
    try {
      told = await run.perform(waiting.signal)
    } catch (error) {
      // The user learns the command failed; whoever looks into why finds the error here.
      console.error(error)
      told = commandFailed(_t('Could not run the command'))
    }
    const outcome = waiting.signal.aborted ? null : told
    running.delete(id)
    if (key !== undefined && runningUnder.get(key) === id) {
      runningUnder.delete(key)
    }
    if (pending !== undefined) {
      settle(id, outcome)
    } else if (outcome) {
      show(outcome)
    }
    return outcome
  }

  function dismiss(id: number): void {
    stopWaiting([id])
    items.value = items.value.filter((item) => item.id !== id)
  }

  function dropOutcomes(): void {
    items.value = items.value.filter(isRunning)
  }

  function clear(): void {
    stopWaiting(running.keys())
    items.value = []
  }

  return {
    items: computed(() => items.value),
    runningKeys: computed(() => new Set(runningUnder.keys())),
    show,
    track,
    dropOutcomes,
    dismiss,
    clear
  }
}
