/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowSelectionState } from '@tanstack/vue-table'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import {
  type ActionFeedbackStack,
  useActionFeedbackStack
} from '@/monitoring/shared/services/useActionFeedbackStack'

export interface MonitoringActions<Id extends string = string> {
  activeAction: Ref<Id | null>
  selectedCount: ComputedRef<number>
  /** One alert per command still running, and how the last one went. */
  feedback: ActionFeedbackStack
  openAction: (id: Id) => void
  closeAction: () => void
  /**
   * Show how the command of the open pane went, and close the pane. The selection stays: a bulk
   * command keeps its rows selected, as in the legacy views.
   */
  applyFeedback: (result: ActionOutcome) => void
}

export function useMonitoringActions<Id extends string = string>(
  rowSelection: Ref<RowSelectionState>,
  selectableKeys: Ref<readonly string[]>
): MonitoringActions<Id> {
  const activeAction = ref<Id | null>(null) as Ref<Id | null>
  const feedback = useActionFeedbackStack()

  const selectedCount = computed(() => Object.values(rowSelection.value).filter(Boolean).length)

  function openAction(id: Id): void {
    activeAction.value = id
  }

  function closeAction(): void {
    activeAction.value = null
  }

  function applyFeedback(result: ActionOutcome): void {
    feedback.show(result)
    closeAction()
  }

  watch(selectableKeys, (keys) => {
    const onOffer = new Set(keys)
    const kept = Object.entries(rowSelection.value).filter(
      ([key, selected]) => selected && onOffer.has(key)
    )
    if (kept.length !== Object.keys(rowSelection.value).length) {
      rowSelection.value = Object.fromEntries(kept)
    }
  })

  watch(selectedCount, (count) => {
    if (count === 0) {
      closeAction()
    }
  })

  return {
    activeAction,
    selectedCount,
    feedback,
    openAction,
    closeAction,
    applyFeedback
  }
}
