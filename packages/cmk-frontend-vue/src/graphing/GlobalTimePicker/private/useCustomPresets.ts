/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { DateTimeRange } from '@/components/date-time'

import { durationSeconds, endsNow, rollingRange } from './timeRange'

export interface CustomPreset {
  id: string
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

  // The range we last wrote; anything else came from elsewhere -> highlight snaps to "Custom".
  let appliedRange: DateTimeRange | null = null

  // Highlight the seeded default: it has no preset identity, so adopt it by matching duration once.
  const initialPreset = endsNow(range.value)
    ? presets.value.find((preset) => preset.totalSeconds === durationSeconds(range.value))
    : undefined
  if (initialPreset) {
    appliedRange = range.value
    activePresetId.value = initialPreset.id
  }

  function applyPreset(preset: CustomPreset): void {
    appliedRange = rollingRange(preset.totalSeconds)
    activePresetId.value = preset.id
    range.value = appliedRange
  }

  watch(range, (value) => {
    if (value !== appliedRange) {
      activePresetId.value = null
    }
  })

  return { presets, activePresetId, applyPreset }
}
