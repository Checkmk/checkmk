/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { instantToParts, isRangeInverted } from 'cmk-ui-library/components/date-time/dateTimeUtils'
import type { RangeDraft, RangePreset } from 'cmk-ui-library/components/date-time/types'
import { useRangePresets } from 'cmk-ui-library/components/date-time/useRangePresets'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, test } from 'vitest'
import { shallowRef } from 'vue'

import { TZ_BERLIN } from './dateTimeTestFixtures'

const zoned = (
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number
): ZonedDateTime =>
  toZoned(new CalendarDateTime(year, month, day, hour, minute), TZ_BERLIN, 'compatible')

const P1: RangePreset = {
  id: 'p1',
  label: untranslated('P1'),
  getRange: () => ({ from: zoned(2026, 3, 9, 8, 0), to: zoned(2026, 3, 10, 9, 0) })
}
const P2: RangePreset = {
  id: 'p2',
  label: untranslated('P2'),
  getRange: () => ({ from: zoned(2026, 4, 1, 0, 0), to: zoned(2026, 4, 2, 0, 0) })
}
// An inverted preset: its from is strictly after its to.
const P_INV: RangePreset = {
  id: 'pinv',
  label: untranslated('Pinv'),
  getRange: () => ({ from: zoned(2026, 5, 2, 9, 0), to: zoned(2026, 5, 1, 8, 0) })
}

const emptyDraft = (): RangeDraft => ({
  from: { date: null, time: null },
  to: { date: null, time: null }
})

const setup = (presets: RangePreset[] = [P1, P2]) => {
  const draft = shallowRef<RangeDraft>(emptyDraft())
  const { selectedPreset, CUSTOM_PRESET_ID } = useRangePresets({
    presets: () => presets,
    draft,
    timeZone: () => TZ_BERLIN
  })
  return { draft, selectedPreset, CUSTOM_PRESET_ID }
}

describe('useRangePresets', () => {
  test('selectedPreset.get initial is custom', () => {
    const { selectedPreset, CUSTOM_PRESET_ID } = setup()
    expect(selectedPreset.value).toBe(CUSTOM_PRESET_ID)
  })

  test('selectedPreset.set valid id applies the preset range', () => {
    const { draft, selectedPreset } = setup()

    selectedPreset.value = 'p1'

    expect(draft.value).toEqual({
      from: instantToParts(P1.getRange().from, TZ_BERLIN),
      to: instantToParts(P1.getRange().to, TZ_BERLIN)
    })
    expect(selectedPreset.value).toBe('p1')
  })

  test('selectedPreset.set custom leaves the draft untouched', () => {
    const { draft, selectedPreset, CUSTOM_PRESET_ID } = setup()
    const before = draft.value

    selectedPreset.value = CUSTOM_PRESET_ID

    expect(selectedPreset.value).toBe(CUSTOM_PRESET_ID)
    expect(draft.value).toBe(before)
  })

  test('selectedPreset.set unknown id is a no-op', () => {
    const { draft, selectedPreset, CUSTOM_PRESET_ID } = setup()
    const before = draft.value

    selectedPreset.value = 'nope'

    expect(selectedPreset.value).toBe(CUSTOM_PRESET_ID)
    expect(draft.value).toBe(before)
  })

  test('hand edit snaps to Custom', () => {
    const { draft, selectedPreset, CUSTOM_PRESET_ID } = setup()
    selectedPreset.value = 'p1'

    draft.value = {
      from: { date: draft.value.from.date, time: { hour: 10, minute: 0 } },
      to: draft.value.to
    }

    expect(selectedPreset.value).toBe(CUSTOM_PRESET_ID)
  })

  test('a draft that spells a preset range selects that preset', () => {
    const { draft, selectedPreset } = setup()

    draft.value = {
      from: instantToParts(P1.getRange().from, TZ_BERLIN),
      to: instantToParts(P1.getRange().to, TZ_BERLIN)
    }

    expect(selectedPreset.value).toBe('p1')
  })

  test('a redrafted copy of the same range keeps the preset selected', () => {
    const { draft, selectedPreset } = setup()
    selectedPreset.value = 'p1'

    draft.value = { from: { ...draft.value.from }, to: { ...draft.value.to } }

    expect(selectedPreset.value).toBe('p1')
  })

  test('picking Custom holds although the range still spells a preset', () => {
    const { selectedPreset, CUSTOM_PRESET_ID } = setup()
    selectedPreset.value = 'p1'

    selectedPreset.value = CUSTOM_PRESET_ID

    expect(selectedPreset.value).toBe(CUSTOM_PRESET_ID)
  })

  test('the Custom pin expires when the draft is written again', () => {
    const { draft, selectedPreset, CUSTOM_PRESET_ID } = setup()
    selectedPreset.value = 'p1'
    selectedPreset.value = CUSTOM_PRESET_ID

    draft.value = { from: { ...draft.value.from }, to: { ...draft.value.to } }

    expect(selectedPreset.value).toBe('p1')
  })

  test('inverted preset is ordered on selection', () => {
    const { draft, selectedPreset } = setup([P1, P_INV])

    selectedPreset.value = 'pinv'

    expect(isRangeInverted(draft.value)).toBe(false)
    expect(draft.value.from.date?.toString()).toBe('2026-05-01')
    expect(draft.value.to.date?.toString()).toBe('2026-05-02')
    expect(selectedPreset.value).toBe('pinv')
  })
})
