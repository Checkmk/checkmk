/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type MaybeRefOrGetter, type Ref } from 'vue'

import { formatRelativeTimeRange } from './formatRelativeTimeRange'
import { useNowTicker } from './useNowTicker'
import { useResolvedDateTimeSettings } from './useResolvedDateTimeSettings'

/**
 * Formats the absolute "start – end" text of a range of `durationSeconds` ending now, or `null`
 * without a duration. While `active`, it re-reads the clock each minute so the text stays current.
 */
export function useRelativeTimeRangeText(
  active: Ref<boolean>,
  timeZone?: MaybeRefOrGetter<string | undefined>
): (durationSeconds: number | null) => string | null {
  const settings = useResolvedDateTimeSettings(undefined, timeZone)
  const now = useNowTicker(active)
  return (durationSeconds) =>
    durationSeconds === null ? null : formatRelativeTimeRange(now.value, durationSeconds, settings)
}
