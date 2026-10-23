/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The window a downtime is scheduled for.
 *
 * The operator picks it in their own time zone through the shared date and time
 * control — the same one Checkmk's own "Schedule downtime" action uses — and
 * Checkmk is told in UTC. Both modals that schedule downtime ask for the same
 * window, and both have to refuse the same nonsense: an end that is not after
 * its start.
 */
import { getLocalTimeZone, now } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types'
import { computed, shallowRef } from 'vue'

/** How long a downtime lasts unless the operator says otherwise. */
const DEFAULT_HOURS = 1

export function useDowntimeWindow() {
  const from = now(getLocalTimeZone())
  // Shallow: a range is replaced whole, and its endpoints are immutable
  // objects a deep ref would wrap in a proxy.
  const range = shallowRef<DateTimeRange>({ from, to: from.add({ hours: DEFAULT_HOURS }) })

  const isValid = computed(() => range.value.to.compare(range.value.from) > 0)

  /** The window as Checkmk takes it. Only meaningful while ``isValid``. */
  function asIso(): { start: string; end: string } {
    return {
      start: range.value.from.toDate().toISOString(),
      end: range.value.to.toDate().toISOString()
    }
  }

  return { range, isValid, asIso }
}
