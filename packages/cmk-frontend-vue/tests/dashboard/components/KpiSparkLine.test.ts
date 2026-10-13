/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import KpiSparkLine from '@/dashboard/components/CmkKpiStatCard/KpiSparkLine.vue'
// Pointer-driven hover/scrub tests live in CmkKpiStatCard.test.ts instead - scrubbing
// is driven via this component's exposed methods, which testing-library can't reach
// without @vue/test-utils (disallowed here).
import type { KpiValueRange, TimestampedSample } from '@/dashboard/components/CmkKpiStatCard/types'

function sample(timestamp: number, value: number | null): TimestampedSample {
  return { timestamp, value }
}

function renderSparkLine(
  series: TimestampedSample[],
  props: { fadeToFloor?: boolean; range?: KpiValueRange } = {}
) {
  return render(KpiSparkLine, {
    props: { series, color: 'var(--color-corporate-green-50)', ...props }
  })
}

function crosshairOf(container: Element): Element | null {
  return container.querySelector('.db-kpi-spark-line__crosshair')
}

function linePathOf(container: Element): string {
  return container.querySelector('.db-kpi-spark-line__line')?.getAttribute('d') ?? ''
}

function areaOf(container: Element): SVGPathElement | null {
  return container.querySelector('.db-kpi-spark-line__area')
}

function dotOf(container: Element): SVGPathElement | null {
  return container.querySelector('.db-kpi-spark-line__dot')
}

function ticksOf(container: Element): SVGPathElement[] {
  return [...container.querySelectorAll<SVGPathElement>('.db-kpi-spark-line__tick')]
}

test('positions samples by their timestamp, not by array index', () => {
  const { container: even } = renderSparkLine([sample(0, 0), sample(60, 10), sample(120, 20)])
  const { container: uneven } = renderSparkLine([sample(0, 0), sample(10, 10), sample(120, 20)])

  expect(linePathOf(even)).not.toBe(linePathOf(uneven))
})

test('breaks the line into separate subpaths at a null sample', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, null), sample(120, 20)])

  const pathData = linePathOf(container)
  expect(pathData.match(/M/g)?.length).toBeGreaterThan(1)
})

test('draws nothing for fewer than two non-null samples', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, null)])

  expect(linePathOf(container)).toBe('')
  expect(dotOf(container)).toBeNull()
})

test('marks the latest non-null sample with a dot', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, 20), sample(120, null)])

  expect(dotOf(container)).not.toBeNull()
})

test('draws no dot when there is nothing to plot', () => {
  const { container } = renderSparkLine([])

  expect(dotOf(container)).toBeNull()
})

test('fades stroke and fill left to right via a shared mask', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, 20)])

  const maskedGroup = container.querySelector('.db-kpi-spark-line g[mask]')
  expect(maskedGroup?.contains(areaOf(container))).toBe(true)
  expect(maskedGroup?.contains(container.querySelector('.db-kpi-spark-line__line'))).toBe(true)
})

test('fills flat by default', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, 20)])

  expect(areaOf(container)).toHaveAttribute('fill', 'currentColor')
  expect(areaOf(container)).toHaveAttribute('fill-opacity', '0.35')
})

test('fades the fill towards the floor when asked to', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, 20)], { fadeToFloor: true })

  const fill = areaOf(container)?.getAttribute('fill') ?? ''
  expect(fill).toMatch(/^url\(#/)
  expect(areaOf(container)).not.toHaveAttribute('fill-opacity')
})

test('auto-scales to the data when no range is given', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, 20)])

  expect(ticksOf(container)).toHaveLength(0)
})

test('clamps samples outside a manual range and marks them with a tick', () => {
  const { container } = renderSparkLine([sample(0, 5), sample(60, 50), sample(120, 95)], {
    range: { minimum: 10, maximum: 90 }
  })

  expect(ticksOf(container)).toHaveLength(2)
})

test('offers no crosshair when there is nothing to plot', () => {
  const { container } = renderSparkLine([sample(0, 10), sample(60, null)])

  expect(crosshairOf(container)).toBeNull()
})
