/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, ref, watch } from 'vue'

import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import { prepareRun } from '@/monitoring/shared/components/action/run'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import {
  type ActionFeedbackStack,
  useActionFeedbackStack
} from '@/monitoring/shared/services/useActionFeedbackStack'

export interface SlideInActions<Target> {
  /** The action whose form pane is on screen, taking the panel over. */
  activeActionId: Ref<string | null>
  /** The actions performing right away, each pulsing until it settles. */
  runningActionIds: ComputedRef<ReadonlySet<string>>
  /** One alert per action running right away, and how the last action went. */
  alerts: ActionFeedbackStack
  /** Performs the action outright when it needs no input, else opens its form. */
  openAction: (actionId: string) => Promise<void>
  closeAction: () => void
  /** Records the outcome of an action performed elsewhere, e.g. from the header's action menu. */
  applyFeedback: (result: ActionOutcome) => void
  perform: (actionId: string, targets: Target[]) => Promise<void>
}

/**
 * The action state a monitoring slide-in keeps for the one object it details: which action is
 * open, which is running, and the alerts telling how they go. Shared so the host and service panels
 * cannot drift apart.
 *
 * `subject` is the object on show; the state resets whenever it changes, so a panel switched to
 * another row never carries the previous one's alerts or open form over.
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
  // An action run for the object on show stops waiting once another is on show or the panel is
  // gone - a reschedule waits for its check - and its outcome is no longer this panel's to tell.
  const alerts = useActionFeedbackStack()

  watch(subject, () => {
    alerts.clear()
    activeActionId.value = null
  })

  function applyFeedback(result: ActionOutcome): void {
    alerts.show(result)
    activeActionId.value = null
    onPerformed(result)
  }

  async function perform(actionId: string, on: Target[]): Promise<void> {
    const action = actions()[actionId]
    if (!action || on.length === 0) {
      return
    }
    // An action picked again while it runs is not run again. The outcome leaves alone a form the
    // user has opened meanwhile.
    const outcome = await alerts.track({ ...prepareRun(action, on), key: actionId })
    if (outcome) {
      onPerformed(outcome)
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
    // A form opened drops how the last action went, but an action performed right away still
    // tells it runs.
    alerts.dropOutcomes()
    activeActionId.value = actionId
  }

  function closeAction(): void {
    activeActionId.value = null
  }

  return {
    activeActionId,
    // Run under their ids, the actions running are those whose alerts tell they run.
    runningActionIds: alerts.runningKeys,
    alerts,
    openAction,
    closeAction,
    applyFeedback,
    perform
  }
}
