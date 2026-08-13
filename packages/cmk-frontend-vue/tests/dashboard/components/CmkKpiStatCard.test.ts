/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard/CmkKpiStatCard.vue'
import type { CmkKpiStatCardProps } from '@/dashboard/components/CmkKpiStatCard/types'

const SERIES = [10, 20, 15, 30]

function renderCard(props: Partial<CmkKpiStatCardProps> = {}) {
  return render(CmkKpiStatCard, {
    props: {
      value: '801.84',
      unit: 'GB',
      series: SERIES,
      color: 'var(--color-corporate-green-50)',
      ...props
    }
  })
}

function deltaOf(container: Element): HTMLElement | null {
  return container.querySelector('.db-cmk-kpi-stat-card__delta')
}

test('renders the headline value with its unit', () => {
  const { container } = renderCard()

  expect(container.querySelector('.db-cmk-kpi-stat-card__value')).toHaveTextContent('801.84')
  expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toHaveTextContent('GB')
})

test('omits the unit element for plain counts', () => {
  const { container } = renderCard({ unit: undefined })

  expect(container.querySelector('.db-cmk-kpi-stat-card__unit')).toBeNull()
})

test('hides the delta indicator when no ratio is given', () => {
  const { container } = renderCard()

  expect(deltaOf(container)).toBeNull()
})

test('shows the delta as an absolute percentage with its direction', () => {
  const { container } = renderCard({ deltaRatio: -0.062 })

  const delta = deltaOf(container)
  expect(delta).toHaveTextContent('6.2%')
  expect(delta).toHaveClass('db-cmk-kpi-stat-card__delta--down')
})

test('an upward delta carries no direction modifier', () => {
  const { container } = renderCard({ deltaRatio: 0.12 })

  expect(deltaOf(container)).not.toHaveClass('db-cmk-kpi-stat-card__delta--down')
})

test('a neutral metric renders the delta in the plain foreground color', () => {
  const { container } = renderCard({ deltaRatio: 0.12 })

  expect(deltaOf(container)?.style.getPropertyValue('--pill-color')).toBe(
    'var(--color-mid-grey-50)'
  )
})

test('an increase on an "up is bad" metric renders red', () => {
  const { container } = renderCard({ deltaRatio: 0.12, deltaSemantics: 'bad' })

  expect(deltaOf(container)?.style.getPropertyValue('--pill-color')).toBe(
    'var(--color-light-red-50)'
  )
})

test('a decrease on an "up is bad" metric renders green', () => {
  const { container } = renderCard({ deltaRatio: -0.12, deltaSemantics: 'bad' })

  expect(deltaOf(container)?.style.getPropertyValue('--pill-color')).toBe(
    'var(--color-corporate-green-50)'
  )
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

  const paths = [...container.querySelectorAll('.db-kpi-spark-line path')]
  expect(paths).toHaveLength(2)
  for (const path of paths) {
    expect(path.getAttribute('d')).toMatch(/^M/)
  }
})

test.each([[[]], [[42]]])('draws no spark line for %j, which cannot make one', (series) => {
  const { container } = renderCard({ series })

  expect(container.querySelector('.db-kpi-spark-line')).toBeNull()
})

test('centers the state against the card, not against the value row', () => {
  const { container } = renderCard({ state: { severity: 'warn' } })

  // Positioned absolutely against the card, so it has to be the card's child --
  // the value row is itself positioned and would capture it.
  expect(
    container.querySelector('.db-cmk-kpi-stat-card > .db-cmk-kpi-stat-card__state')
  ).not.toBeNull()
  expect(
    container.querySelector('.db-cmk-kpi-stat-card__value-row .db-cmk-kpi-stat-card__state')
  ).toBeNull()
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
  ['ok', 'OK', 'cmk-badge--success'],
  ['warn', 'WARN', 'cmk-badge--warning'],
  ['crit', 'CRIT', 'cmk-badge--danger'],
  ['unknown', 'UNKN', 'cmk-badge--unknown'],
  ['pending', 'PEND', 'cmk-badge--default']
] as const)('labels the %s state %s in its own color', (severity, label, colorClass) => {
  const { container } = renderCard({ state: { severity } })

  const badge = container.querySelector('.db-cmk-kpi-stat-card__state')
  expect(badge).toHaveTextContent(label)
  expect(badge).toHaveClass(colorClass)
})

test('a state alone does not tint the card', () => {
  const { container } = renderCard({ state: { severity: 'crit' } })

  expect(container.querySelector('.db-cmk-kpi-stat-card')).not.toHaveClass(
    'db-cmk-kpi-stat-card--tinted'
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
