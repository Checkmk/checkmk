/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Translate Maps metric series into what ``TimeSeriesGraph`` draws.
 *
 * Two things get bridged. Values: Maps stores raw perfdata, the graph expects
 * the metric registry's canonical unit, so the registry's translation scale is
 * applied here. Units: the registry's unit spec is already shaped like the unit
 * the graph's metadata carries and only has to be handed over without its scale,
 * since the values arrive scaled. A metric the registry does not know goes
 * through the same two steps
 * with the spec ``fallbackUnitSpec`` reads off its raw unit, so there is one
 * path rather than a registered and an unregistered one.
 */
import type { HorizontalLine, Metric } from '@/graphing/components/TimeSeriesGraph'
import type { MetricPoint, MetricUnitMap, MetricUnitSpec } from '@/maps/types/api'
import { fallbackUnitSpec } from '@/maps/utils/metricFormat'

import { type SampleGrid, resampleOnGrid } from './resample'

/** What a caller knows about the metrics behind one graph. */
export interface SeriesContext {
  /** Registry display units per raw perfdata label, where the GUI resolved any. */
  unitMap?: MetricUnitMap | undefined
  /** Registry series colours per raw perfdata label. */
  colorMap?: Record<string, string> | undefined
  /** Registry display titles per raw perfdata label. */
  titles?: Record<string, string> | undefined
  /** Raw perfdata labels drawn below the axis (bidirectional graphs). */
  mirroredKeys?: string[] | undefined
  /** Perfdata unit to read a fallback spec off, for labels with no registry entry. */
  fallbackUnit?: string | undefined
  /**
   * Colours for labels the registry has none for, resolved from the map view's
   * palette custom properties (see ``useMapPalette``).
   */
  palette: readonly string[]
}

/** The unit a series is formatted in — the spec's, minus its scale. */
export function unitFormatOf(spec: MetricUnitSpec): Metric['metadata']['unit'] {
  return {
    notation: spec.notation,
    symbol: spec.symbol,
    precision: spec.precision,
    // The maps metric registry carries no convertibility concept, so its specs
    // have no such field. The graph's unit requires one; its producer defaults
    // it to true when the shared unit format leaves it open
    // (ApiUnitFormat.from_shared), and this matches that.
    convertible: true
  }
}

/**
 * The display spec of one raw perfdata label: the registry's where there is
 * one, else the SI/time reading of the unit the samples carry.
 */
function specOf(key: string, points: MetricPoint[], context: SeriesContext): MetricUnitSpec {
  return context.unitMap?.[key] ?? fallbackUnitSpec(points.at(-1)?.unit ?? context.fallbackUnit)
}

function colorOf(key: string, index: number, context: SeriesContext): string {
  const registered = context.colorMap?.[key]
  if (registered) {
    return registered
  }
  // Read through a modulo, so a palette that resolved to nothing (a consumer
  // mounted outside the map view, or a unit test) degrades to the inherited
  // colour rather than an undefined access.
  return context.palette.length === 0
    ? 'currentColor'
    : context.palette[index % context.palette.length]!
}

/**
 * The colour each series is drawn in, keyed by raw perfdata label — so a legend
 * beside the graph can label the curves without re-deriving the rule.
 */
export function seriesColorMap(
  metricKeys: string[],
  context: SeriesContext
): Record<string, string> {
  return Object.fromEntries(metricKeys.map((key, index) => [key, colorOf(key, index, context)]))
}

export function buildGraphMetrics(
  data: Record<string, MetricPoint[]>,
  metricKeys: string[],
  grid: SampleGrid,
  context: SeriesContext
): Metric[] {
  const mirrored = new Set(context.mirroredKeys ?? [])
  return metricKeys.map((key, index) => {
    const points = data[key] ?? []
    const spec = specOf(key, points, context)
    const scaled = points.map((point) => ({ ...point, value: point.value * spec.scale }))
    return {
      data_points: resampleOnGrid(scaled, grid),
      metadata: {
        color: colorOf(key, index, context),
        name: key,
        title: context.titles?.[key] ?? key,
        unit: unitFormatOf(spec),
        // A curve built from a map object's own performance data comes from no
        // series, so it carries no series attributes — the model's empty case.
        attributes: []
      },
      // Mirroring is the graph's own ``inverse``: it negates the curve and
      // centres the value axis on zero — what a bidirectional graph's lower
      // half needs.
      render: { hidden: false, inverse: mirrored.has(key), stack: null }
    }
  })
}

/** The warn/crit levels of the graph's leading metric, as graph guide lines. */
export function buildThresholdLines(
  thresholds: { warn: number | null; crit: number | null } | null,
  data: Record<string, MetricPoint[]>,
  leadingKey: string | undefined,
  context: SeriesContext,
  labels: { warn: string; crit: string },
  colors: { warn: string; crit: string }
): HorizontalLine[] {
  if (!thresholds || leadingKey === undefined) {
    return []
  }
  const spec = specOf(leadingKey, data[leadingKey] ?? [], context)
  const unit = unitFormatOf(spec)
  const lines: HorizontalLine[] = []
  for (const name of ['warn', 'crit'] as const) {
    const raw = thresholds[name]
    if (raw !== null) {
      lines.push({
        color: colors[name],
        name,
        title: labels[name],
        unit,
        value: raw * spec.scale
      })
    }
  }
  return lines
}
