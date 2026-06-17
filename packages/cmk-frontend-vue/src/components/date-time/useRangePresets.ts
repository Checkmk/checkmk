/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, nextTick, ref, watch } from 'vue'

import { instantToParts, isRangeInverted, swapRangeEndpoints } from './dateTimeUtils'
import type { RangeDraft, RangePreset } from './types'

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
  /** Group v-model for the preset radios: reads the active id; on a user pick, applies the preset's
   *  range or snaps to manual. */
  selectedPreset: Ref<string>
  CUSTOM_PRESET_ID: string
}

export function useRangePresets(options: RangePresetsOptions): RangePresets {
  const { presets, draft, timeZone } = options
  const selectedPresetId = ref<string>(CUSTOM_PRESET_ID)

  // Set while a preset-driven draft write is in flight, so the snap-to-custom watch below doesn't
  // mistake the preset's own write for a manual edit.
  let applyingPreset = false

  function selectPreset(preset: RangePreset): void {
    const { from, to } = preset.getRange()
    applyingPreset = true
    const candidate: RangeDraft = {
      from: instantToParts(from, timeZone()),
      to: instantToParts(to, timeZone())
    }
    // A committed range is always ordered; order it on selection rather than waiting for a blur.
    draft.value = isRangeInverted(candidate) ? swapRangeEndpoints(candidate) : candidate
    selectedPresetId.value = preset.id
    void nextTick(() => {
      applyingPreset = false
    })
  }

  const selectedPreset = computed<string>({
    get: () => selectedPresetId.value,
    set: (id) => {
      if (id === CUSTOM_PRESET_ID) {
        selectedPresetId.value = CUSTOM_PRESET_ID
        return
      }
      const preset = presets()?.find((candidate) => candidate.id === id)
      if (preset) {
        selectPreset(preset)
      }
    }
  })

  watch(draft, () => {
    if (!applyingPreset) {
      selectedPresetId.value = CUSTOM_PRESET_ID
    }
  })

  return { selectedPreset, CUSTOM_PRESET_ID }
}
