/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, computed, ref, watch } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import type { AggregationNode } from '@/maps/types/api'
import {
  BI_STATE_LABEL,
  aggregationLeafId,
  flattenAggregationLeaves
} from '@/maps/utils/aggregationTree'
import { compileRegex } from '@/maps/utils/regex'

/** How the count reads: nothing matched, everything matched, or somewhere in
 *  between — plus the case of a pattern that is not a regex at all. */
export type FilterFeedbackTone = 'invalid' | 'warn' | 'matched' | 'muted'

export interface FilterFeedback {
  text: TranslatedString
  tone: FilterFeedbackTone
}

interface ExcludeMembersPreviewOptions {
  connectionId: () => string
  aggregationId: () => string
  excludeMembers: () => string
  excludeMemberStates: () => string
}

/**
 * Live "N of M leaves hidden" preview for the BI `exclude_members` filter. The
 * aggregation tree is fetched once per aggregation id (depth 10 = the API cap,
 * so the count reflects every leaf), then the suppression count recomputes
 * locally as the operator types the member regex / state list — no per-keystroke
 * round-trip. A leaf is suppressed when every *defined* filter matches it.
 */
export function useExcludeMembersPreview(options: ExcludeMembersPreviewOptions): {
  feedback: ComputedRef<FilterFeedback | null>
} {
  const { connectionId, aggregationId, excludeMembers, excludeMemberStates } = options
  const { objects } = useMapsApis()
  const { _t } = usei18n()

  const excludeMembersTree = ref<AggregationNode | null>(null)

  watch(
    () => [aggregationId(), connectionId()] as const,
    async ([aggId, cid]) => {
      if (!aggId || !cid) {
        excludeMembersTree.value = null
        return
      }
      try {
        // Fixed depth=10 = the API cap; "every leaf" guarantees the
        // count reflects the full aggregation, not just the
        // currently-displayed subtree.
        const result = await objects.fetchAggregationTree(aggId, 10)
        excludeMembersTree.value = result.tree
      } catch {
        excludeMembersTree.value = null
      }
    },
    { immediate: true }
  )

  const feedback = computed<FilterFeedback | null>(() => {
    const tree = excludeMembersTree.value
    if (!tree) {
      return null
    }
    const memberRe = excludeMembers().trim()
    const stateList = excludeMemberStates()
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
    if (!memberRe && stateList.length === 0) {
      return null
    }

    let regex: RegExp | null = null
    if (memberRe) {
      try {
        // Pattern is operator-typed and only used to test against the
        // already-fetched leaves array — no server round-trip and no
        // unbounded input source. compileRegex centralises the eslint
        // tradeoff for security/detect-non-literal-regexp so we can
        // keep using the standard linter elsewhere.
        regex = compileRegex(memberRe)
      } catch {
        return { text: _t('Invalid regular expression.'), tone: 'invalid' }
      }
    }

    const leaves = flattenAggregationLeaves(tree)
    const total = leaves.length
    let suppressed = 0
    for (const l of leaves) {
      const key = aggregationLeafId(l)
      const matchesMember = regex ? regex.test(key) : true
      const matchesState = stateList.length
        ? stateList.includes(BI_STATE_LABEL[l.state] ?? '')
        : true
      // Both are true where their filter is absent, and the case where both
      // are absent returned above -- so this is "every filter given matches".
      if (matchesMember && matchesState) {
        suppressed += 1
      }
    }

    if (suppressed === 0) {
      return {
        text: _t('0 of %{total} leaves hidden — filter matches nothing.', { total }),
        tone: 'muted'
      }
    }
    if (suppressed >= total) {
      return {
        text: _t('All %{count} leaves would be hidden — the filter is too broad.', {
          count: suppressed,
          total
        }),
        tone: 'warn'
      }
    }
    return {
      text: _t('%{count} of %{total} leaves will be hidden.', { count: suppressed, total }),
      tone: 'matched'
    }
  })

  return { feedback }
}
