/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { instantToParts, isRangeInverted, swapRangeEndpoints } from './dateTimeUtils'
import type { RangeDraft, RangePreset } from './types'

/** The staged endpoints a preset spells in `timeZone`, ordered start before end. */
export function presetDraft(preset: RangePreset, timeZone: string): RangeDraft {
  const { from, to } = preset.getRange()
  const candidate: RangeDraft = {
    from: instantToParts(from, timeZone),
    to: instantToParts(to, timeZone)
  }
  return isRangeInverted(candidate) ? swapRangeEndpoints(candidate) : candidate
}
