/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'

import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard/CmkKpiStatCard.vue'
import type {
  CmkKpiStatCardProps,
  TimestampedSample
} from '@/dashboard/components/CmkKpiStatCard/types'

function sample(timestamp: number, value: number | null): TimestampedSample {
  return { timestamp, value }
}

const SERIES = [sample(0, 10), sample(60, 20), sample(120, 15), sample(180, 30)]

function formatValue(value: number): string {
  return value.toFixed(1)
}

function renderCard(props: Partial<CmkKpiStatCardProps> = {}) {
  return render(CmkKpiStatCard, {
    props: {
      value: '801.84',
      unit: 'GB',
      series: SERIES,
      color: 'var(--color-corporate-green-50)',
      formatValue,
      ...props
    }
  })
}

function deltaOf(container: Element): HTMLElement | null {
  return container.querySelector('.db-cmk-kpi-stat-card__delta')
}

function deltaPercentOf(container: Element): string | undefined {
  return container.querySelector('.db-cmk-kpi-stat-card__delta-percent')?.textContent
}

function deltaComparisonOf(container: Element): string | undefined {
  return container.querySelector('.db-cmk-kpi-stat-card__delta-comparison')?.textContent
}

const { formatter: durationFormatter } = userSpecificUnit(
  { notation: 'time', symbol: 's', precision: { type: 'auto', digits: 0 } },
  'celsius'
)

test('renders the headline value with its unit', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card__value')).toHaveTextContent('801.84')
  expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toHaveTextContent('GB')
})

test('omits the unit element for plain counts', () => {
  const { container } = renderCard({ unit: undefined })

  expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toBeNull()
})

test('hides the delta indicator when fewer than two real samples exist', () => {
  const { container } = renderCard({ series: [sample(0, 42)] })

  expect(deltaOf(container)).toBeNull()
})

test('hides the delta indicator when showDelta is false', () => {
  const { container } = renderCard({ showDelta: false })

  expect(deltaOf(container)).toBeNull()
})

test('compares the current value against the average of the samples before it by default', () => {
  // Basis (average of 10, 20, 15) = 15; current = 30 -> up 100.0%.
  const { container } = renderCard()

  const delta = deltaOf(container)
  expect(delta).not.toHaveClass('db-cmk-kpi-stat-card__delta--down')
  expect(deltaPercentOf(container)).toBe('100.0%')
  expect(deltaComparisonOf(container)).toBe(`vs. 15.0 avg. (${durationFormatter.render(180)})`)
})

test('shows a downward delta when the current value is below the basis', () => {
  // Basis (average of 10, 30) = 20; current = 5 -> down 75.0%.
  const series = [sample(0, 10), sample(60, 30), sample(120, 5)]
  const { container } = renderCard({ series })

  expect(deltaOf(container)).toHaveClass('db-cmk-kpi-stat-card__delta--down')
  expect(deltaPercentOf(container)).toBe('75.0%')
})

test.each([
  ['average', '15.0'],
  ['last', '15.0'],
  ['minimum', '10.0'],
  ['maximum', '20.0'],
  ['median', '15.0']
] as const)(
  'compares against the %s of the real samples before the current one',
  (basis, expected) => {
    const { container } = renderCard({ comparisonBasis: basis })

    expect(deltaComparisonOf(container)).toContain(`vs. ${expected}`)
  }
)

test('the "last" basis reads as "prev. sample" with no window suffix', () => {
  // Series is [10, 20, 15, 30]; current is 30, so the basis is the sample
  // immediately before it (15), not the whole basis window's own average.
  const { container } = renderCard({ comparisonBasis: 'last' })

  expect(deltaComparisonOf(container)).toBe('vs. 15.0 prev. sample')
})

test('the comparison basis and window come from real samples only, excluding the current one', () => {
  const series = [sample(0, 10), sample(60, null), sample(120, 20), sample(180, 30)]
  const { container } = renderCard({ series })

  // Real basis samples are 10 (t=0) and 20 (t=120); current is 30 (t=180).
  // The null at t=60 is skipped, and the window runs to the current sample's
  // own timestamp, not the gap's.
  expect(deltaComparisonOf(container)).toBe(`vs. 15.0 avg. (${durationFormatter.render(180)})`)
})

test('the value and sparkline take the given accent color', () => {
  const { container } = renderCard({ color: 'var(--color-light-red-50)' })

  const card = container.querySelector<HTMLElement>('.db-cmk-kpi-stat-card')
  expect(card?.style.getPropertyValue('--accent-color')).toBe('var(--color-light-red-50)')
  expect(container.querySelector<SVGElement>('.db-kpi-spark-line')?.style.color).toBe(
    'var(--color-light-red-50)'
  )
})

test('draws a line and an area path for the series', () => {
  const { container } = renderCard()

  const paths = [
    ...container.querySelectorAll('.db-kpi-spark-line__line, .db-kpi-spark-line__area')
  ]
  expect(paths).toHaveLength(2)
  for (const path of paths) {
    expect(path.getAttribute('d')).toMatch(/^M/)
  }
})

test.each([[[]], [[sample(0, 42)]]])(
  'draws no spark line for %j, which cannot make one',
  (series) => {
    const { container } = renderCard({ series })

    expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
  }
)

test('draws a broken line for a series with a gap, without crashing', () => {
  const series = [sample(0, 10), sample(60, null), sample(120, 20)]
  const { container } = renderCard({ series })

  const linePath = container.querySelector('.db-kpi-spark-line__line')
  const pathData = linePath?.getAttribute('d') ?? ''
  expect(pathData).toMatch(/^M/)
  expect(pathData.match(/M/g)?.length).toBeGreaterThan(1)
})

test('bridges a gap bounded by real samples with a dashed, hatched fill', () => {
  const series = [sample(0, 10), sample(60, null), sample(120, 20)]
  const { container } = renderCard({ series })

  const bridgeLine = container.querySelector('.db-kpi-spark-line__bridge-line')
  const bridgeArea = container.querySelector('.db-kpi-spark-line__bridge-area')
  expect(bridgeLine).toHaveAttribute('stroke-dasharray')
  expect(bridgeArea?.getAttribute('fill')).toMatch(/^url\(#/)
})

test('draws no bridge for a series without gaps', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-kpi-spark-line__bridge-line')).toBeNull()
})

test('replaces the delta with a stale note when the series ends in missing samples', () => {
  const series = [sample(0, 10), sample(60, 20), sample(120, null)]
  const { container } = renderCard({ series })

  expect(deltaOf(container)).toBeNull()
  expect(container.querySelector('.db-cmk-kpi-stat-card__stale-note')).toHaveTextContent(
    'No recent data'
  )
})

test('shows the delta, not a stale note, for a series that ends with real data', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card__stale-note')).toBeNull()
  expect(deltaOf(container)).not.toBeNull()
})

test('an interior gap does not make the reading stale', () => {
  const series = [sample(0, 10), sample(60, null), sample(120, 20)]
  const { container } = renderCard({ series })

  expect(container.querySelector('.db-cmk-kpi-stat-card__stale-note')).toBeNull()
  expect(deltaOf(container)).not.toBeNull()
})

test('positions the state against the card, not against the value row', () => {
  const { container } = renderCard({ state: { severity: 'warn' } })

  // Positioned absolutely against the card (top right, every variant), so it must be the card's child.
  expect(
    container.querySelector('.db-cmk-kpi-stat-card > .db-cmk-kpi-stat-card__state')
  ).not.toBeNull()
  expect(
    container.querySelector('.db-cmk-kpi-stat-card__value-row .db-cmk-kpi-stat-card__state')
  ).toBeNull()
})

test('keeps the state badge in the same corner even with no spark line', () => {
  const { container } = renderCard({ series: [], state: { severity: 'warn' } })

  expect(
    container.querySelector('.db-cmk-kpi-stat-card > .db-cmk-kpi-stat-card__state')
  ).not.toBeNull()
})

test('gives the whole card to the value when there is no spark line', () => {
  const { container } = renderCard({ series: [] })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass(
    'db-cmk-kpi-stat-card--value-only'
  )
})

test('leaves the value its usual corner when a spark line is drawn', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--value-only'
  )
})

test('renders the value as plain text without a link target', () => {
  const { container } = renderCard()

  expect(container.querySelector('a')).toBeNull()
})

test('links the value when given a target', () => {
  const { container } = renderCard({ href: 'view.py?view_name=service' })

  expect(container.querySelector('a')).toHaveAttribute('href', 'view.py?view_name=service')
})

test('shows no state badge by default', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card__state')).toBeNull()
})

test.each([
  ['ok', 'OK', 'cmk-state-tag--ok'],
  ['warn', 'WARN', 'cmk-state-tag--warning'],
  ['crit', 'CRIT', 'cmk-state-tag--critical'],
  ['unknown', 'UNKN', 'cmk-state-tag--unknown'],
  ['pending', 'PEND', 'cmk-state-tag--pending']
] as const)('labels the %s state %s in its own tone', (severity, label, toneClass) => {
  const { container } = renderCard({ state: { severity } })

  const badge = container.querySelector('.db-cmk-kpi-stat-card__state')
  expect(badge).toHaveTextContent(label)
  expect(badge).toHaveClass(toneClass)
})

test('keeps the badge on the last known state, marked stale, when the reading is stale', () => {
  const series = [sample(0, 10), sample(60, 20), sample(120, null)]
  const { container } = renderCard({ series, state: { severity: 'warn' } })

  const badge = container.querySelector('.db-cmk-kpi-stat-card__state')
  expect(badge).toHaveTextContent('WARN')
  expect(badge).toHaveClass('cmk-state-tag--stale')
})

test('renders an em dash and a body note instead of a value when there is no data', () => {
  const { container } = renderCard({ value: undefined, unit: 'GB' })

  expect(container.querySelector('.db-cmk-kpi-stat-card__value')).toHaveTextContent('—')
  expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toHaveTextContent('GB')
  expect(deltaOf(container)).toBeNull()
  expect(container.querySelector('.db-cmk-kpi-stat-card__no-data-note')).not.toBeNull()
})

test('draws no curve and no state badge when there is no data', () => {
  const { container } = renderCard({ value: undefined, state: { severity: 'crit' } })

  expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
  expect(container.querySelector('.db-cmk-kpi-stat-card__state')).toBeNull()
})

test('a no-data card keeps its normal top-left layout, unlike a curve-less metric', () => {
  const { container } = renderCard({ value: undefined, series: [] })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--value-only'
  )
})

test('a state alone does not tint a no-data card', () => {
  const { container } = renderCard({
    value: undefined,
    state: { severity: 'crit', tintBackground: true }
  })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--tinted'
  )
})

test('a state alone does not tint the card', () => {
  const { container } = renderCard({ state: { severity: 'crit' } })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--tinted'
  )
  expect(container.querySelector('.db-kpi-spark-line__area')).toHaveAttribute(
    'fill',
    'currentColor'
  )
})

test('tints the card in the state color when asked to', () => {
  const { container } = renderCard({
    state: { severity: 'crit', tintBackground: true }
  })

  const card = container.querySelector<HTMLElement>('.db-cmk-kpi-stat-card')
  expect(card).toHaveClass('db-cmk-kpi-stat-card--tinted')
  expect(card?.style.getPropertyValue('--tint-color')).toBe('var(--color-danger)')
})

test('fades the sparkline fill towards the floor when the card is tinted', () => {
  const { container } = renderCard({
    state: { severity: 'crit', tintBackground: true }
  })

  const fill = container.querySelector('.db-kpi-spark-line__area')?.getAttribute('fill') ?? ''
  expect(fill).toMatch(/^url\(#/)
})

test('defaults to full height, with a scrim protecting the numbers', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--band'
  )
  expect(container.querySelector('.db-cmk-kpi-stat-card__scrim')).not.toBeNull()
})

test('band mode reserves the sparkline below the numbers, with no scrim', () => {
  const { container } = renderCard({ sparkHeightMode: 'band' })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).toHaveClass('db-cmk-kpi-stat-card--band')
  expect(container.querySelector('.db-cmk-kpi-stat-card__scrim')).toBeNull()
})

test('a value-only card is neither banded nor scrimmed - there is nothing to protect', () => {
  const { container } = renderCard({ series: [], sparkHeightMode: 'band' })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--band'
  )
  expect(container.querySelector('.db-cmk-kpi-stat-card__scrim')).toBeNull()
})

test('omits the range labels unless limits are given', () => {
  const { container } = renderCard()

  expect(container.querySelectorAll('.db-cmk-kpi-stat-card__range')).toHaveLength(0)
})

test('labels both ends of the displayed range', () => {
  const { container } = renderCard({ rangeLimits: { minimum: '0 B', maximum: '1.00 GB' } })

  expect(container.querySelector('.db-cmk-kpi-stat-card__range--minimum')).toHaveTextContent('0 B')
  expect(container.querySelector('.db-cmk-kpi-stat-card__range--maximum')).toHaveTextContent(
    '1.00 GB'
  )
})
