/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import DonutOtherBreakdownOverview from '@/network-flow/slide-ins/DonutOtherBreakdownSlideIn/DonutOtherBreakdownOverview.vue'
import type { ComputedNetworkFlowDonutOtherBreakdown } from '@/network-flow/slide-ins/api/context'

const BREAKDOWN: ComputedNetworkFlowDonutOtherBreakdown = {
  dimension: 'applications',
  categories: [
    { label: 'TLS', value: 30_000_000, previous_value: 20_000_000, share: 60 },
    { label: 'DNS', value: 10_000_000, previous_value: 0, share: 20 }
  ],
  total: 50_000_000,
  previous_total: 45_000_000,
  category_count: 2
}

function renderOverview(data: Partial<ComputedNetworkFlowDonutOtherBreakdown> = {}) {
  return render(DonutOtherBreakdownOverview, { props: { data: { ...BREAKDOWN, ...data } } })
}

function headers(container: Element): (string | undefined)[] {
  return [...container.querySelectorAll('th')].map((el) => el.textContent?.trim())
}

test('names the dimension the categories belong to', () => {
  expect(headers(renderOverview().container)[0]).toBe('Application')
  expect(headers(renderOverview({ dimension: 'protocols' }).container)[0]).toBe('Protocol')
})

test('compares against the preceding window once there is one', () => {
  const { container } = renderOverview()

  expect(headers(container)).toEqual(['Application', 'Share', 'Current', 'Previous', 'Change'])
})

test('drops the comparison columns when there is no history to compare against', () => {
  const { container } = renderOverview({ previous_total: 0 })

  // A collector started minutes ago would otherwise report every category as new.
  expect(headers(container)).toEqual(['Application', 'Share', 'Current'])
})

test('renders share, volume and change per category', () => {
  const { container } = renderOverview()

  const cells = [...container.querySelectorAll('tbody tr')].map((row) =>
    [...row.querySelectorAll('td')].map((el) => el.textContent?.trim())
  )
  expect(cells).toEqual([
    // The sign is the arrow's to carry, so it is not in the text.
    ['TLS', '60.0%', '30 MB', '20 MB', '50.0%'],
    // Growth out of nothing has no ratio, so it says "new".
    ['DNS', '20.0%', '10 MB', '0 B', 'new']
  ])
})

test('points the change the way it went, and only where it went somewhere', () => {
  const { container } = renderOverview()

  const arrows = [...container.querySelectorAll('.db-cmk-delta-arrow')]
  // TLS grew; "new" has no ratio to point along.
  expect(arrows).toHaveLength(1)
  expect(arrows[0]).not.toHaveClass('db-cmk-delta-arrow--down')
})

test('turns the arrow over for a category that shrank', () => {
  const { container } = renderOverview({
    categories: [{ label: 'TLS', value: 20_000_000, previous_value: 30_000_000, share: 100 }],
    category_count: 1
  })

  expect(container.querySelector('.db-cmk-delta-arrow')).toHaveClass('db-cmk-delta-arrow--down')
})

test('sums up what is behind the slice', () => {
  const { container } = renderOverview()

  expect(container).toHaveTextContent('2 applications')
  expect(container).toHaveTextContent('50 MB')
})

test('says the ring held nothing back rather than showing an empty table', () => {
  const { container } = renderOverview({ categories: [], category_count: 0 })

  expect(container.querySelector('table')).toBeNull()
  expect(container).toHaveTextContent('The ranked categories account for all traffic the ring')
})

test('admits to a capped list when the tail is longer than the rows', () => {
  const { container } = renderOverview({ category_count: 7 })

  expect(container).toHaveTextContent('Showing the largest 2 of 7 applications.')
})

test('stays quiet about capping when every category is listed', () => {
  const { container } = renderOverview()

  expect(container).not.toHaveTextContent('Showing the largest')
})
