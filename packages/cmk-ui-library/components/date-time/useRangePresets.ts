/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, shallowRef } from 'vue'

import { instantToParts, isRangeInverted, swapRangeEndpoints } from './dateTimeUtils'
import type { DateTimePartsDraft, RangeDraft, RangePreset } from './types'

/** Reserved id for the auto-appended manual-range entry; presets must not reuse it. */
export const CUSTOM_PRESET_ID = 'custom'

export interface RangePresetsOptions {
  /** The configured presets (getter, so it stays reactive to the prop). */
  presets: () => RangePreset[] | undefined
  /** The staged range; selecting a preset replaces its `.value`. */
  draft: Ref<RangeDraft>
  /** Getter so the resolved timezone stays reactive. */
  timeZone: () => string
}

export interface RangePresets {
  /** Group v-model for the preset radios: reads the preset the staged range spells, and on a pick
   *  applies that preset's range or pins the manual entry. */
  selectedPreset: Ref<string>
  CUSTOM_PRESET_ID: string
}

function endpointsEqual(left: DateTimePartsDraft, right: DateTimePartsDraft): boolean {
  const sameDate =
    left.date === null
      ? right.date === null
      : right.date !== null && left.date.compare(right.date) === 0
  const sameTime =
    left.time === null
      ? right.time === null
      : right.time !== null &&
        left.time.hour === right.time.hour &&
        left.time.minute === right.time.minute
  return sameDate && sameTime
}

export function useRangePresets(options: RangePresetsOptions): RangePresets {
  const { presets, draft, timeZone } = options

  const pinnedCustomDraft = shallowRef<RangeDraft | null>(null)

  function presetDraft(preset: RangePreset): RangeDraft {
    const { from, to } = preset.getRange()
    const candidate: RangeDraft = {
      from: instantToParts(from, timeZone()),
      to: instantToParts(to, timeZone())
    }
    return isRangeInverted(candidate) ? swapRangeEndpoints(candidate) : candidate
  }

  const matchingPresetId = computed<string>(() => {
    const match = presets()?.find((preset) => {
      const candidate = presetDraft(preset)
      return (
        endpointsEqual(candidate.from, draft.value.from) &&
        endpointsEqual(candidate.to, draft.value.to)
      )
    })
    return match?.id ?? CUSTOM_PRESET_ID
  })

  const selectedPreset = computed<string>({
    get: () =>
      pinnedCustomDraft.value === draft.value ? CUSTOM_PRESET_ID : matchingPresetId.value,
    set: (id) => {
      if (id === CUSTOM_PRESET_ID) {
        pinnedCustomDraft.value = draft.value
        return
      }
      const preset = presets()?.find((candidate) => candidate.id === id)
      if (preset) {
        draft.value = presetDraft(preset)
      }
    }
  })

  return { selectedPreset, CUSTOM_PRESET_ID }
}
