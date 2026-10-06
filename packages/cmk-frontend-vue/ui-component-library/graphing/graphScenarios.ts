/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone } from '@internationalized/date'

import type {
  BinUnit,
  HorizontalLine,
  Metric,
  MetricRender,
  TimeRange
} from '@/graphing/components/TimeSeriesGraph'
import type { TimeInterval } from '@/graphing/types'
import { binnedTimeAxis } from '@/graphing/utils/timeRange'

export type Scenario = 'lines' | 'areas' | 'stacked' | 'bars' | 'coarse-bars' | 'mixed'

export interface ScenarioData {
  metrics: Metric[]
  dataTimeRange: TimeRange
  binUnit: BinUnit | undefined
  horizontalLines: HorizontalLine[]
}

type Unit = Metric['metadata']['unit']
type Series = (time: number) => number | null

const HOUR = 3600
const DAY = 24 * HOUR
const SAMPLES_PER_WINDOW = 720

const COUNT: Unit = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'strict', digits: 0 },
  convertible: false
}
const LOAD: Unit = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: false
}
const PERCENT: Unit = {
  notation: 'decimal',
  symbol: '%',
  precision: { type: 'auto', digits: 2 },
  convertible: false
}
const THROUGHPUT: Unit = {
  notation: 'iec',
  symbol: 'B/s',
  precision: { type: 'auto', digits: 2 },
  convertible: false
}

const LINE: MetricRender = { shape: 'line', inverse: false, hidden: false }

function area(stack: string, inverse = false): MetricRender {
  return { shape: 'area', stack, inverse, hidden: false }
}

function bar(stack: string | null): MetricRender {
  return { shape: 'bar', stack, aggregation: 'sum', inverse: false, hidden: false }
}

function wave(time: number, period: number, phase = 0): number {
  return Math.sin((2 * Math.PI * time) / period + phase)
}

/** A pseudo random number in [0, 1) that is the same for the same time and seed. */
function jitter(time: number, seed: number): number {
  const value = Math.sin(time * 12.9898 + seed * 78.233) * 43758.5453
  return value - Math.floor(value)
}

/** Busy during the local working day, quiet at night. */
function workingDay(time: number): number {
  return 0.5 + 0.5 * wave(time - 9 * HOUR, DAY, -Math.PI / 2)
}

/** A few events per grid value, more during the working day. */
function events(seed: number, perHour: number, step: number): Series {
  return (time) =>
    Math.floor(jitter(time, seed) * perHour * (step / HOUR) * (0.3 + workingDay(time)))
}

function metric(name: string, unit: Unit, color: string, render: MetricRender, series: Series) {
  return { name, unit, color, render, series }
}

type MetricSpec = ReturnType<typeof metric>

function sampled(specs: MetricSpec[], timeRange: TimeRange): Metric[] {
  const count = (timeRange.end - timeRange.start) / timeRange.step
  const times = Array.from(
    { length: count },
    (_, index) => timeRange.start + (index + 1) * timeRange.step
  )
  return specs.map((spec) => ({
    metadata: {
      name: spec.name,
      title: spec.name,
      unit: spec.unit,
      color: spec.color,
      attributes: []
    },
    render: spec.render,
    data_points: times.map(spec.series)
  }))
}

function sampleGrid(window: TimeInterval): TimeRange {
  const step = Math.max(60, Math.round((window.end - window.start) / SAMPLES_PER_WINDOW / 60) * 60)
  return {
    start: Math.floor(window.start / step) * step,
    end: Math.ceil(window.end / step) * step,
    step
  }
}

const HOURLY_AXIS = binnedTimeAxis('hour', getLocalTimeZone())

function binGrid(window: TimeInterval): TimeRange {
  return HOURLY_AXIS.planFetchWindow(window, 0)
}

function coarseGrid(window: TimeInterval, step: number): TimeRange {
  const { start, end } = binGrid(window)
  return { start: Math.floor(start / step) * step, end: Math.ceil(end / step) * step, step }
}

function horizontalLine(name: string, value: number, color: string): HorizontalLine {
  return { name, title: name, value, unit: LOAD, color }
}

function sampledScenario(specs: MetricSpec[], window: TimeInterval): ScenarioData {
  const dataTimeRange = sampleGrid(window)
  return {
    metrics: sampled(specs, dataTimeRange),
    dataTimeRange,
    binUnit: undefined,
    horizontalLines: []
  }
}

function binnedScenario(
  specs: (step: number) => MetricSpec[],
  dataTimeRange: TimeRange
): ScenarioData {
  return {
    metrics: sampled(specs(dataTimeRange.step), dataTimeRange),
    dataTimeRange,
    binUnit: 'hour',
    horizontalLines: []
  }
}

/** The dummy data of a scenario over the window, on a grid that covers it. */
export function scenarioData(scenario: Scenario, window: TimeInterval): ScenarioData {
  switch (scenario) {
    case 'lines':
      return {
        ...sampledScenario(
          [
            metric(
              'CPU load',
              LOAD,
              '#00b9ff',
              LINE,
              (t) => 2.4 + 1.6 * wave(t, 6 * HOUR) + 0.3 * jitter(t, 1)
            ),
            metric(
              'Load average 15 min',
              LOAD,
              '#ff9b3d',
              LINE,
              (t) => 2.4 + 1.2 * wave(t, 6 * HOUR, -0.6)
            ),
            metric('Sporadic probe', LOAD, '#b46cff', LINE, (t) =>
              wave(t, 9 * HOUR) > 0.8 ? null : 1 + 0.5 * wave(t, 90 * 60)
            )
          ],
          window
        ),
        horizontalLines: [
          horizontalLine('Warning', 4.5, '#ffd000'),
          horizontalLine('Critical', 5.5, '#ff3232')
        ]
      }
    case 'areas':
      return sampledScenario(
        [
          metric(
            'Inbound',
            THROUGHPUT,
            '#00c8a0',
            area('in'),
            (t) => 40e6 * (0.6 + 0.3 * wave(t, DAY) + 0.1 * jitter(t, 3))
          ),
          metric(
            'Outbound',
            THROUGHPUT,
            '#1e64ff',
            area('out', true),
            (t) => 15e6 * (0.5 + 0.35 * wave(t, DAY, 1) + 0.15 * jitter(t, 4))
          )
        ],
        window
      )
    case 'stacked':
      return sampledScenario(
        [
          metric(
            'User',
            PERCENT,
            '#36a3ff',
            area('cpu'),
            (t) => 30 + 15 * wave(t, 4 * HOUR) + 5 * jitter(t, 5)
          ),
          metric(
            'System',
            PERCENT,
            '#ff7a45',
            area('cpu'),
            (t) => 12 + 6 * wave(t, 2 * HOUR, 2) + 3 * jitter(t, 6)
          ),
          metric('I/O wait', PERCENT, '#ffc53d', area('cpu'), (t) =>
            Math.max(0, 8 * wave(t, 3 * HOUR, 1) + 4 * jitter(t, 7))
          ),
          metric('Capacity', PERCENT, '#8c8c8c', LINE, () => 90)
        ],
        window
      )
    case 'bars':
      return binnedScenario(
        (step) => [metric('Alerts', COUNT, '#00b9ff', bar(null), events(8, 6, step))],
        binGrid(window)
      )
    case 'coarse-bars':
      return binnedScenario(
        (step) => [metric('Alerts', COUNT, '#00b9ff', bar(null), events(8, 6, step))],
        coarseGrid(window, 6 * HOUR)
      )
    case 'mixed':
      return binnedScenario(
        (step) => [
          metric('Host notifications', COUNT, '#1e64ff', bar('notifications'), events(9, 3, step)),
          metric(
            'Service notifications',
            COUNT,
            '#00c8a0',
            bar('notifications'),
            events(10, 8, step)
          ),
          metric('Expected per hour', COUNT, '#ff9b3d', LINE, (t) => 11 * (0.3 + workingDay(t)))
        ],
        binGrid(window)
      )
  }
}
