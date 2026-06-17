/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import type { CustomGraphTimeRange } from 'cmk-shared-typing/typescript/global_time_picker'
import { describe, expect, test } from 'vitest'
import { type Ref, nextTick, shallowRef } from 'vue'

import type { DateTimeRange } from '@/components/date-time'

import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'
import { useCustomPresets } from '@/graphing/GlobalTimePicker/private/useCustomPresets'

const TZ = 'Europe/Berlin'

// A range of exactly `totalSeconds`, anchored at a fixed instant so durations are deterministic.
const rangeOfSeconds = (totalSeconds: number): DateTimeRange => {
  const to: ZonedDateTime = toZoned(new CalendarDateTime(2026, 3, 10, 12, 0), TZ, 'compatible')
  return { from: to.subtract({ seconds: totalSeconds }), to }
}

const RANGES: CustomGraphTimeRange[] = [
  { title: 'Last 4 hours', total_seconds: 4 * 3600 },
  { title: 'Last 25 hours', total_seconds: 25 * 3600 }
]

// A range whose duration matches no preset, so the highlight starts at "Custom".
const NON_MATCHING = 12345

function setup(
  ranges: CustomGraphTimeRange[] = RANGES,
  initialRange: DateTimeRange = rangeOfSeconds(NON_MATCHING)
) {
  const range: Ref<DateTimeRange> = shallowRef(initialRange)
  return { range, ...useCustomPresets(() => ranges, range) }
}

describe('useCustomPresets', () => {
  test('maps the configured ranges to presets with labels and unique ids', () => {
    const { presets } = setup()
    expect(presets.value.map(({ label, totalSeconds }) => ({ label, totalSeconds }))).toEqual([
      { label: 'Last 4 hours', totalSeconds: 4 * 3600 },
      { label: 'Last 25 hours', totalSeconds: 25 * 3600 }
    ])
    expect(new Set(presets.value.map((preset) => preset.id)).size).toBe(2)
  })

  test('ids are content-derived, so they survive reordering of the configured ranges', () => {
    const idOf = (label: string, presets: { id: string; label: string }[]) =>
      presets.find((preset) => preset.label === label)!.id

    const original = setup().presets.value
    const reordered = setup([RANGES[1]!, RANGES[0]!]).presets.value

    expect(idOf('Last 4 hours', reordered)).toBe(idOf('Last 4 hours', original))
    expect(idOf('Last 25 hours', reordered)).toBe(idOf('Last 25 hours', original))
  })

  test('exact-duplicate ranges still get distinct ids (stable Vue keys)', () => {
    const duplicate: CustomGraphTimeRange = { title: 'Last 4 hours', total_seconds: 4 * 3600 }
    const { presets } = setup([duplicate, { ...duplicate }])
    expect(new Set(presets.value.map((preset) => preset.id)).size).toBe(2)
  })

  test('applyPreset writes a span of total_seconds to the model and highlights it', () => {
    const { range, presets, applyPreset, activePresetId } = setup()
    const target = presets.value[0]!
    applyPreset(target)

    const spanMs = range.value.to.toDate().getTime() - range.value.from.toDate().getTime()
    expect(spanMs).toBe(4 * 3600 * 1000)
    expect(activePresetId.value).toBe(target.id)
  })

  test('applyPreset keeps its own highlight (does not snap to Custom)', async () => {
    const { presets, applyPreset, activePresetId } = setup()
    const target = presets.value[1]!
    applyPreset(target)
    await nextTick()
    expect(activePresetId.value).toBe(target.id)
  })

  test('an external range change snaps the highlight back to Custom', async () => {
    const { range, presets, applyPreset, activePresetId } = setup()
    applyPreset(presets.value[0]!)
    await nextTick()
    expect(activePresetId.value).not.toBeNull()

    // e.g. the user edits the range in the flyout, or a graph pans/zooms.
    range.value = rangeOfSeconds(99)
    await nextTick()
    expect(activePresetId.value).toBeNull()
  })

  test('highlights the seeded rolling default on load when its duration matches a preset', () => {
    const { presets, activePresetId } = setup(RANGES, rollingRange(4 * 3600))
    expect(activePresetId.value).toBe(presets.value[0]!.id)
  })

  test('does not highlight a fixed past window that merely shares a preset duration', () => {
    const { activePresetId } = setup(RANGES, rangeOfSeconds(4 * 3600))
    expect(activePresetId.value).toBeNull()
  })

  test('no highlight on load when the range matches no preset', () => {
    const { activePresetId } = setup(RANGES, rollingRange(NON_MATCHING))
    expect(activePresetId.value).toBeNull()
  })

  test('no highlight on load when there are no presets', () => {
    const { activePresetId } = setup([], rollingRange(4 * 3600))
    expect(activePresetId.value).toBeNull()
  })
})
