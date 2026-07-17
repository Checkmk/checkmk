/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowSelectionState } from '@tanstack/vue-table'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'

export interface MonitoringActions<Id extends string = string> {
  activeAction: Ref<Id | null>
  selectedCount: ComputedRef<number>
  feedback: Ref<ActionFeedback | null>
  feedbackOpen: Ref<boolean>
  openAction: (id: Id) => void
  closeAction: () => void
  applyFeedback: (result: ActionFeedback, options?: { clearSelection?: boolean }) => void
}

export function useMonitoringActions<Id extends string = string>(
  rowSelection: Ref<RowSelectionState>
): MonitoringActions<Id> {
  const activeAction = ref<Id | null>(null) as Ref<Id | null>
  const feedback = ref<ActionFeedback | null>(null)
  const feedbackOpen = ref(false)

  const selectedCount = computed(() => Object.values(rowSelection.value).filter(Boolean).length)

  function openAction(id: Id): void {
    activeAction.value = id
  }

  function closeAction(): void {
    activeAction.value = null
  }

  function applyFeedback(result: ActionFeedback, options: { clearSelection?: boolean } = {}): void {
    // Row-level actions act on a single host and must not touch the (independent) bulk selection.
    if (result.variant === 'success' && (options.clearSelection ?? true)) {
      rowSelection.value = {}
    }
    feedback.value = result
    feedbackOpen.value = true
    closeAction()
  }

  watch(selectedCount, (count) => {
    if (count === 0) {
      closeAction()
    }
  })

  return {
    activeAction,
    selectedCount,
    feedback,
    feedbackOpen,
    openAction,
    closeAction,
    applyFeedback
  }
}
