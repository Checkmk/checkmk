/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, ref, watch } from 'vue'

import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'

export interface SlideInActions<Target> {
  /** The action whose form pane is on screen, taking the panel over. */
  activeActionId: Ref<string | null>
  /** The action performing right away, pulsing until it settles. */
  runningActionId: Ref<string | null>
  feedback: Ref<ActionFeedback | null>
  feedbackOpen: Ref<boolean>
  /** Performs the action outright when it needs no input, else opens its form. */
  openAction: (actionId: string) => Promise<void>
  closeAction: () => void
  /** Records the outcome of an action performed elsewhere, e.g. from the header's action menu. */
  applyFeedback: (result: ActionFeedback) => void
  perform: (actionId: string, targets: Target[]) => Promise<void>
}

/**
 * The action state a monitoring slide-in keeps for the one object it details: which action is
 * open, which is running, and the outcome of the last one. Shared so the host and service panels
 * cannot drift apart.
 *
 * `subject` is the object on show; the state resets whenever it changes, so a panel switched to
 * another row never carries the previous one's feedback or open form over.
 */
export function useSlideInActions<Target>(
  actions: () => MonitoringActionRegistry<Target>,
  targets: ComputedRef<Target[]>,
  subject: () => unknown,
  onPerformed: (result: ActionFeedback) => void
): SlideInActions<Target> {
  const activeActionId = ref<string | null>(null)
  const runningActionId = ref<string | null>(null)
  const feedback = ref<ActionFeedback | null>(null)
  const feedbackOpen = ref(false)

  watch(subject, () => {
    activeActionId.value = null
    runningActionId.value = null
    feedback.value = null
  })

  function applyFeedback(result: ActionFeedback): void {
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
    runningActionId.value = actionId
    try {
      applyFeedback(await action.perform(on, action.defaultValues()))
    } finally {
      runningActionId.value = null
    }
  }

  async function openAction(actionId: string): Promise<void> {
    if (!(actionId in actions())) {
      return
    }
    if (actionId === RESCHEDULE_ACTION_ID) {
      await perform(actionId, targets.value)
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
