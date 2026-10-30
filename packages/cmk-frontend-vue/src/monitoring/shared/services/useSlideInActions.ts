/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, ref, watch } from 'vue'

import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'

export interface SlideInActions<Target> {
  /** The action whose form pane is on screen, taking the panel over. */
  activeActionId: Ref<string | null>
  /** The action performing right away, pulsing until it settles. */
  runningActionId: Ref<string | null>
  feedback: Ref<ActionOutcome | null>
  feedbackOpen: Ref<boolean>
  /** Performs the action outright when it needs no input, else opens its form. */
  openAction: (actionId: string) => Promise<void>
  closeAction: () => void
  /** Records the outcome of an action performed elsewhere, e.g. from the header's action menu. */
  applyFeedback: (result: ActionOutcome) => void
  perform: (actionId: string, targets: Target[]) => Promise<void>
}

/**
 * The action state a monitoring slide-in keeps for the one object it details: which action is
 * open, which is running, and the outcome of the last one. Shared so the host and service panels
 * cannot drift apart.
 *
 * `subject` is the object on show; the state resets whenever it changes, so a panel switched to
 * another row never carries the previous one's feedback or open form over.
 *
 * `targets` is asked per action, because not every action acts on the object on show: a service
 * whose check is a byproduct of the agent-based check reschedules the host's "Check_MK" service.
 */
export function useSlideInActions<Target>(
  actions: () => MonitoringActionRegistry<Target>,
  targets: (actionId: string) => Target[],
  subject: () => unknown,
  onPerformed: (result: ActionOutcome) => void
): SlideInActions<Target> {
  const activeActionId = ref<string | null>(null)
  const runningActionId = ref<string | null>(null)
  const feedback = ref<ActionOutcome | null>(null)
  const feedbackOpen = ref(false)

  // An action run for the object on show stops waiting once another is on show or the panel is
  // gone - a reschedule waits for its check - and its outcome is no longer this panel's to tell.
  let shown = new AbortController()
  onScopeDispose(() => shown.abort())

  watch(subject, () => {
    shown.abort()
    shown = new AbortController()
    activeActionId.value = null
    runningActionId.value = null
    feedback.value = null
  })

  function applyFeedback(result: ActionOutcome): void {
    feedback.value = result
    feedbackOpen.value = true
    activeActionId.value = null
    onPerformed(result)
  }

  async function perform(actionId: string, on: Target[]): Promise<void> {
    const action = actions()[actionId]
    if (!action || on.length === 0) {
      return
    }
    const { signal } = shown
    runningActionId.value = actionId
    try {
      const result = await action.perform(on, action.defaultValues(), signal)
      if (!signal.aborted) {
        applyFeedback(result)
      }
    } finally {
      if (!signal.aborted) {
        runningActionId.value = null
      }
    }
  }

  async function openAction(actionId: string): Promise<void> {
    if (!(actionId in actions())) {
      return
    }
    if (actionId === RESCHEDULE_ACTION_ID) {
      await perform(actionId, targets(actionId))
      return
    }
    feedback.value = null
    activeActionId.value = actionId
  }

  function closeAction(): void {
    activeActionId.value = null
  }

  return {
    activeActionId,
    runningActionId,
    feedback,
    feedbackOpen,
    openAction,
    closeAction,
    applyFeedback,
    perform
  }
}
