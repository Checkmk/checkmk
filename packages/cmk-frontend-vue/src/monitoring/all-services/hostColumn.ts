/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, shallowRef, watch } from 'vue'

import { SUBPIXEL_SLACK } from '@/monitoring/shared/components/MonitoringTableContext'
import { HOST_CELL_CHROME } from '@/monitoring/shared/components/cell/hostCell'
import type { TextWidth } from '@/monitoring/shared/components/timestampColumns'
import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

interface HostListing {
  readonly items: Readonly<Ref<readonly { host_name: string }[]>>
  readonly fetchState: Readonly<Ref<FetchState>>
}

/**
 * The width the host column needs for the longest host name in the listing. Null while text can't
 * be measured.
 *
 * Only grows while the listing refreshes in the background, so the column doesn't change width on
 * every refresh, and starts afresh with the rows a new query brings. Measures each host name once
 * per query, however many services the host has and however often the listing refreshes, so the
 * cost per refresh is a pass over the rows.
 */
export function useHostColumnWidth(
  listing: HostListing,
  textWidth: Readonly<Ref<TextWidth | null>>
): ComputedRef<number | null> {
  const nameWidths = new Map<string, number>()
  const widestName = shallowRef<number | null>(null)
  // Set by a new query, until its rows arrive.
  let startAfresh = false

  watch(
    listing.fetchState,
    (state) => {
      if (state === 'foreground') {
        startAfresh = true
      }
    },
    { flush: 'sync' }
  )

  watch(
    [listing.items, textWidth],
    ([rows, measure], previous) => {
      if (!measure) {
        widestName.value = null
        return
      }
      const fontChanged = previous !== undefined && measure !== previous[1]
      const fresh = startAfresh || fontChanged
      // Widths in another font are stale, and names of an earlier query needn't stay for the
      // whole session.
      if (fresh) {
        nameWidths.clear()
      }
      // A font arriving while a new query loads must leave its rows to start afresh.
      if (previous === undefined || rows !== previous[0]) {
        startAfresh = false
      }
      const widest = rows.reduce(
        (max, { host_name: name }) => {
          let width = nameWidths.get(name)
          if (width === undefined) {
            width = measure(name)
            nameWidths.set(name, width)
          }
          return Math.max(max, width)
        },
        fresh ? 0 : (widestName.value ?? 0)
      )
      widestName.value = widest
    },
    { immediate: true }
  )

  return computed(() =>
    widestName.value === null
      ? null
      : Math.ceil(widestName.value) + SUBPIXEL_SLACK + HOST_CELL_CHROME
  )
}
