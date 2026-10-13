/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Response, type Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, type MaybeRefOrGetter, type Ref, computed, ref, toValue } from 'vue'

import { useItemDescription } from '../../composables/useItemDescription'
import {
  type Domain,
  type GraphItem,
  type ItemId,
  domainOf,
  isDynamic,
  isFormula
} from '../../types'
import { collectTransitiveDependents } from '../formula'
import type { CommitResult } from '../types'

/** Common percentiles offered as a starting point; any value the user types in [0, 100] is added. */
const COMMON_PERCENTILES = [50, 75, 90, 95, 99]

export interface TransformationEditor {
  selectedId: Ref<ItemId | null>
  /** The percentile as entered; may be a partial/invalid string mid-edit. */
  percentile: Ref<string | null>
  /** Messages of the last failed commit, cleared on the next successful commit or reset. */
  errors: Ref<string[]>
  metricOptions: ComputedRef<Suggestions>
  percentileOptions: Suggestions
  selectItem: (id: ItemId) => void
  /** Build the percentile AST, or the messages explaining why the input is incomplete. */
  commit: () => CommitResult
  reset: () => void
}

/** A percentile in [0, 100], or null if the string is empty/out of range/not a number. */
function parsePercentile(value: string | null): number | null {
  if (value === null || value.trim() === '') {
    return null
  }
  const num = Number(value)
  return Number.isFinite(num) && num >= 0 && num <= 100 ? num : null
}

/** State and rules for the percentile transformation: a single non-dynamic series in `domain` wrapped in a percentile. */
export function useTransformationEditor(
  items: MaybeRefOrGetter<readonly GraphItem[]>,
  domain: Domain,
  editedItemId: MaybeRefOrGetter<ItemId | null> = null
): TransformationEditor {
  const { _t } = usei18n()
  const { describeItem } = useItemDescription()

  const selectedId = ref<ItemId | null>(null)
  const percentile = ref<string | null>(null)
  const errors = ref<string[]>([])

  const eligibleItems = computed(() => {
    const edited = toValue(editedItemId)
    const all = toValue(items)
    const cyclic =
      edited === null
        ? new Set<ItemId>()
        : collectTransitiveDependents(all.filter(isFormula), edited)
    return all.filter(
      (item) =>
        domainOf(item.type) === domain &&
        !isDynamic(item.type) &&
        item.id !== edited &&
        !cyclic.has(item.id)
    )
  })

  const metricOptions = computed<Suggestions>(() => ({
    type: 'fixed',
    suggestions: eligibleItems.value.map((item) => ({
      name: item.id,
      title: untranslated(`${item.id} — ${describeItem(item)}`)
    }))
  }))

  const percentileOptions: Suggestions = {
    type: 'callback-filtered',
    querySuggestions: (query: string) => {
      const trimmed = query.trim()
      const num = Number(trimmed)
      const isCustom = trimmed !== '' && Number.isFinite(num) && num >= 0 && num <= 100
      const values =
        isCustom && !COMMON_PERCENTILES.includes(num)
          ? [num, ...COMMON_PERCENTILES]
          : COMMON_PERCENTILES
      const matching = values.filter(
        (v) => trimmed === '' || String(v).startsWith(trimmed) || v === num
      )
      return Promise.resolve(
        new Response(matching.map((v) => ({ name: String(v), title: untranslated(String(v)) })))
      )
    }
  }

  function selectItem(id: ItemId): void {
    if (eligibleItems.value.some((item) => item.id === id)) {
      selectedId.value = id
    }
  }

  function reset(): void {
    selectedId.value = null
    percentile.value = null
    errors.value = []
  }

  function commit(): CommitResult {
    const value = parsePercentile(percentile.value)
    const messages: string[] = []
    if (selectedId.value === null) {
      messages.push(_t('Select the metric to transform.'))
    }
    if (value === null) {
      messages.push(_t('Enter a percentile between 0 and 100.'))
    }
    errors.value = messages
    if (selectedId.value === null || value === null) {
      return { errors: messages }
    }
    return {
      ast: { op: 'percentile', percentile: value, operand: { op: 'ref', id: selectedId.value } }
    }
  }

  return {
    selectedId,
    percentile,
    errors,
    metricOptions,
    percentileOptions,
    selectItem,
    commit,
    reset
  }
}
