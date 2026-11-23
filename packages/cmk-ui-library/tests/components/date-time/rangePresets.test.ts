/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { presetDraft } from 'cmk-ui-library/components/date-time/rangePresets'
import type { RangePreset } from 'cmk-ui-library/components/date-time/types'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, test } from 'vitest'

import { TZ_BERLIN, TZ_TOKYO } from './dateTimeTestFixtures'

const zoned = (
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number
): ZonedDateTime =>
  toZoned(new CalendarDateTime(year, month, day, hour, minute), TZ_BERLIN, 'compatible')

const preset = (from: ZonedDateTime, to: ZonedDateTime): RangePreset => ({
  id: 'preset',
  label: untranslated('Preset'),
  getRange: () => ({ from, to })
})

describe('presetDraft', () => {
  test('spells the preset range as wall-clock endpoints in the given zone', () => {
    const draft = presetDraft(preset(zoned(2026, 3, 9, 8, 0), zoned(2026, 3, 10, 9, 0)), TZ_TOKYO)

    expect(draft.from.date?.toString()).toBe('2026-03-09')
    expect(draft.from.time).toEqual({ hour: 16, minute: 0 })
    expect(draft.to.date?.toString()).toBe('2026-03-10')
    expect(draft.to.time).toEqual({ hour: 17, minute: 0 })
  })

  test('orders an inverted preset start before end', () => {
    const draft = presetDraft(preset(zoned(2026, 5, 2, 9, 0), zoned(2026, 5, 1, 8, 0)), TZ_BERLIN)

    expect(draft.from.date?.toString()).toBe('2026-05-01')
    expect(draft.to.date?.toString()).toBe('2026-05-02')
  })
})
