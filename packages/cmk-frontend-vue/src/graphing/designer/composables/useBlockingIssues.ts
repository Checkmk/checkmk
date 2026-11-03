/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterDefinitions } from 'cmk-ui-library/components/filter'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import type { DesignerItem } from '../drafts'
import type { ItemId } from '../types'
import { type RowIssue, validateDesign } from '../validation'

export interface BlockingIssues {
  /** Everything that blocks a save, whether or not a save has been tried. */
  blockingIssues: ComputedRef<RowIssue[]>
  /** The blocking issues per row, empty until a save has been tried. */
  issuesByRow: ComputedRef<ReadonlyMap<ItemId, RowIssue[]>>
  /** The rows with blocking issues, in the order of the design. */
  blockedIds: ComputedRef<ItemId[]>
  hasAttemptedSave: Ref<boolean>
}

/** What blocks saving a design, and which of it to show at the rows. */
export function useBlockingIssues(
  items: ComputedRef<readonly DesignerItem[]>,
  getFilterDefinitions: () => FilterDefinitions | null
): BlockingIssues {
  // Until a save has been tried, an unfinished source is work in progress, not an error.
  const hasAttemptedSave = ref(false)
  const blockingIssues = computed(() => validateDesign(items.value, getFilterDefinitions()))
  const issuesByRow = computed(() => {
    const byRow = new Map<ItemId, RowIssue[]>()
    if (!hasAttemptedSave.value) {
      return byRow
    }
    for (const issue of blockingIssues.value) {
      byRow.set(issue.id, [...(byRow.get(issue.id) ?? []), issue])
    }
    return byRow
  })
  const blockedIds = computed(() => {
    const blocked = new Set(blockingIssues.value.map((issue) => issue.id))
    return items.value.filter((item) => blocked.has(item.id)).map((item) => item.id)
  })
  return { blockingIssues, issuesByRow, blockedIds, hasAttemptedSave }
}
