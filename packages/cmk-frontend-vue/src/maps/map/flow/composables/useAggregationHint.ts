/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Whether to still explain why most of a flow map's hosts show only a ring.
 *
 * On a large map the backend sends the per-service detail for the worst hosts
 * and aggregates the rest, or the map would be unusable. The note that says so
 * explains a fixed rule, so once an operator has understood it they can be rid
 * of it for good — kept per user, because a browser shared between two
 * operators should not hide it from the one who has not read it yet.
 */
import { computed, ref, watch } from 'vue'

function storageKey(userId: string | number | undefined): string {
  return `maps.flow.aggregationHintDismissed.${userId ?? 'anon'}`
}

/**
 * Reading it can throw rather than return nothing: where site data is blocked,
 * touching ``window.localStorage`` at all raises. A hint the operator has to
 * dismiss once more is not worth taking the map down for.
 */
function readFlag(key: string): boolean {
  try {
    return window.localStorage?.getItem(key) === '1'
  } catch {
    return false
  }
}

export function useAggregationHint(userId: () => string | number | undefined) {
  // The session usually resolves after the first render, and the dismissal is
  // the user's, so the key follows whoever it turns out to be rather than
  // settling on "anon" for the life of the map.
  const key = computed(() => storageKey(userId()))
  const dismissed = ref(readFlag(key.value))
  watch(key, (current) => {
    dismissed.value = readFlag(current)
  })

  function dismiss(): void {
    dismissed.value = true
    try {
      window.localStorage?.setItem(key.value, '1')
    } catch {
      // Private mode, or storage full: it stays dismissed for this session.
    }
  }

  return { dismissed, dismiss }
}
