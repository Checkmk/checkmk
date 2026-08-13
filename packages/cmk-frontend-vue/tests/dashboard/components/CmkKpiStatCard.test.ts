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

  expect(deltaOf(container)?.style.getPropertyValue('--delta-color')).toBe(
    'var(--color-mid-grey-50)'
  )
})

test('an increase on an "up is bad" metric renders red', () => {
  const { container } = renderCard({ deltaRatio: 0.12, deltaSemantics: 'bad' })

  expect(deltaOf(container)?.style.getPropertyValue('--delta-color')).toBe(
    'var(--color-light-red-50)'
  )
})

test('a decrease on an "up is bad" metric renders green', () => {
  const { container } = renderCard({ deltaRatio: -0.12, deltaSemantics: 'bad' })

  expect(deltaOf(container)?.style.getPropertyValue('--delta-color')).toBe(
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

test('draws no path with fewer than two data points', () => {
  const { container } = renderCard({ series: [42] })

  const paths = [...container.querySelectorAll('.db-kpi-spark-line path')]
  for (const path of paths) {
    expect(path.getAttribute('d')).toBeFalsy()
  }
})
