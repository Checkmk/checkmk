/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { FORMATS_SHOWING_AGES } from '@/monitoring/shared/formatTimestamp'
import type { TimestampFormatId } from '@/monitoring/shared/types'

/** How an age column stands out from the dimmed rest: a recent change, a stale check. */
export type AgeEmphasis = 'plain' | 'recent' | 'stale'

/** The legacy state age painters' `bold_if_younger_than`. */
const RECENT_SECONDS = 10 * 60

/** Like `paint_age`, which marks a recent age only where it shows one, not a date or epoch. */
export function stateAgeEmphasis(
  lastStateChange: number | null | undefined,
  timestampFormat: TimestampFormatId,
  nowSeconds: number = Date.now() / 1000
): AgeEmphasis {
  return FORMATS_SHOWING_AGES.has(timestampFormat) &&
    lastStateChange !== null &&
    lastStateChange !== undefined &&
    nowSeconds - lastStateChange < RECENT_SECONDS
    ? 'recent'
    : 'plain'
}

/** Like the legacy check age painters, which never mark a check age as recent. */
export function checkAgeEmphasis(stale: boolean | undefined): AgeEmphasis {
  return stale === true ? 'stale' : 'plain'
}
