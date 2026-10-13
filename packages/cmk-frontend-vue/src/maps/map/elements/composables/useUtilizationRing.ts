/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The utilisation an object's icon ring shows.
 *
 * The figure comes from Checkmk's Perf-O-Meter, not from the raw perfdata: the
 * Perf-O-Meter definition already knows which metric speaks for a check
 * (``mem_used_percent`` for Memory, ``fs_used_percent`` for Filesystem, …) and
 * applies the plug-in's own unit and threshold colouring. Mirroring it keeps
 * the ring's colour and the icon's state colour telling the same story.
 *
 * Only where no Perf-O-Meter is available does it fall back to the first
 * perfdata field, which is a guess: Memory's ``mem_lnx_total_used`` skews red
 * at half the RAM in use.
 */
import { type Ref, computed } from 'vue'

import { useMapPalette } from '@/maps/map/composables/useMapPalette'
import { type MetricInfoBinding } from '@/maps/map/composables/useMetricInfo'
import { fillSegments, usePerfometer } from '@/maps/map/composables/usePerfometer'
import type { MapElement, ObjectState } from '@/maps/types/api'
import { parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'

import type { RingColors } from './arcRing'

/** Object types and display modes that carry no ring. */
const RINGLESS_TYPES = new Set(['textbox', 'line', 'host', 'image'])
/** States that say "no data": nothing to draw a ring around. */
const RINGLESS_STATES = new Set(['NOT_FOUND', 'NO_PERMISSION'])
const PULSING_STATES = new Set(['DOWN', 'CRITICAL', 'UNREACHABLE'])

export interface UtilizationRing {
  /** Whether this object gets a ring at all. */
  visible: Ref<boolean>
  /** Utilisation to fill, or ``null`` for a plain state ring. */
  pct: Ref<number | null>
  colors: Ref<RingColors>
  pulsing: Ref<boolean>
}

export function useUtilizationRing(source: {
  object: () => MapElement
  state: () => ObjectState | undefined
  connectionId: () => string | undefined
  /** The NagVis-compatible renderer draws no rings. */
  classic: () => boolean
}): UtilizationRing {
  const palette = useMapPalette()
  const stateName = computed(() => source.state()?.state ?? 'PENDING')

  const visible = computed(
    () =>
      !source.classic() &&
      !RINGLESS_TYPES.has(source.object().type) &&
      source.object().display?.mode !== 'gadget' &&
      !RINGLESS_STATES.has(stateName.value)
  )

  const binding: MetricInfoBinding = {
    connectionId: source.connectionId,
    hostName: () => source.object().host_name,
    serviceDescription: () => source.object().service_description,
    perfData: () => source.state()?.perf_data,
    checkCommand: () => source.state()?.check_command,
    enabled: () => !RINGLESS_STATES.has(stateName.value)
  }
  const perfometer = usePerfometer(binding)

  /** Everything in the Perf-O-Meter's first row that is not background filler. */
  const perfometerFill = computed(() => {
    const resolved = perfometer.value
    return resolved && resolved.rows.length ? fillSegments(resolved, 0) : null
  })

  const firstMetricPct = computed(() => {
    const first = parsePerfData(source.state()?.perf_data ?? '')[0]
    return first ? utilPercent(first) : null
  })

  const pct = computed(() => {
    const segments = perfometerFill.value
    if (segments) {
      const total = segments.reduce((sum, segment) => sum + segment.pct, 0)
      return Math.min(100, Math.max(0, total))
    }
    return firstMetricPct.value
  })

  const fill = computed(() => {
    const segments = perfometerFill.value
    if (segments && segments.length > 0) {
      // The dominant segment carries the story; a ring is too small to show a
      // whole stack, and the plug-in already coloured that segment by severity.
      const dominant = segments.reduce(
        (best, segment) => (segment.pct > best.pct ? segment : best),
        segments[0]!
      )
      return dominant.color
    }
    return firstMetricPct.value === null
      ? palette.value.state(stateName.value)
      : utilColor(firstMetricPct.value)
  })

  return {
    visible,
    pct,
    colors: computed(() => ({
      state: palette.value.state(stateName.value),
      fill: fill.value,
      track: palette.value.gaugeTrack
    })),
    pulsing: computed(() => PULSING_STATES.has(stateName.value))
  }
}
