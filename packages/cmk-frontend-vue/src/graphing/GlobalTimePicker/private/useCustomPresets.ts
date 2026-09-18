/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import { durationSeconds, endsNow, rollingRange } from './timeRange'

export interface CustomPreset {
  /** `null` identifies the "Custom" entry that `DynamicPresets` appends to every preset list. */
  id: string | null
  label: TranslatedString
  totalSeconds: number
}

export interface CustomPresets {
  presets: ComputedRef<CustomPreset[]>
  /** The highlighted pill, or `null` for the "Custom" entry. */
  activePresetId: Ref<string | null>
  applyPreset: (preset: CustomPreset) => void
}

export function useCustomPresets(
  customTimeRanges: () => CustomGraphTimeRange[],
  range: Ref<DateTimeRange>
): CustomPresets {
  const presets = computed<CustomPreset[]>(() => {
    // Content-derived ids survive reordering; the `#n` suffix keeps Vue keys unique for duplicates.
    const seen = new Map<string, number>()
    return customTimeRanges().map((timeRange) => {
      const base = `${timeRange.total_seconds}:${timeRange.title}`
      const count = seen.get(base) ?? 0
      seen.set(base, count + 1)
      return {
        id: count === 0 ? base : `${base}#${count}`,
        label: untranslated(timeRange.title),
        totalSeconds: timeRange.total_seconds
      }
    })
  })

  const activePresetId = ref<string | null>(null)

  // The range we last wrote; anything else came from elsewhere -> re-checked against the
  // presets below rather than assumed to be "Custom".
  let appliedRange: DateTimeRange | null = null

  // A range with no preset identity of its own (the seeded default, or one written by a
  // graph zoom/pan/reset) still gets highlighted if it happens to match a preset's duration
  // and end-near-now shape — e.g. resetting a zoom back to an original "Last 1 h" selection
  // should re-highlight "Last 1 h" rather than fall to "Custom".
  function matchingPreset(value: DateTimeRange): CustomPreset | undefined {
    const duration = durationSeconds(value)
    return endsNow(value)
      ? presets.value.find((preset) => preset.totalSeconds === duration)
      : undefined
  }

  function applyPreset(preset: CustomPreset): void {
    appliedRange = rollingRange(preset.totalSeconds)
    activePresetId.value = preset.id
    range.value = appliedRange
  }

  // `immediate` also seeds the default: the first run matches range.value against the
  // presets exactly as any later change would.
  watch(
    range,
    (value) => {
      if (value === appliedRange) {
        return
      }
      appliedRange = value
      activePresetId.value = matchingPreset(value)?.id ?? null
    },
    { immediate: true }
  )

  return { presets, activePresetId, applyPreset }
}
