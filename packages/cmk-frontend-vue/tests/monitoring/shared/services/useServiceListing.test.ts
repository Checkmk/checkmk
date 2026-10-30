/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useServiceListing } from '@/monitoring/shared/services/useServiceListing'

test('labels a selection of services', () => {
  const listing = useServiceListing({})

  expect(listing.selectionLabel(2)).toBe('Selected services: 2')
  expect(listing.countsLabel(1, 5)).toBe('Selected service: 1 | Total services: 5')
})

test('filters for unhandled service problems', () => {
  const listing = useServiceListing({})

  expect(listing.quickFilters).toEqual([
    expect.objectContaining({
      label: 'Unhandled service problems',
      filter: {
        type: 'and',
        children: [
          { type: 'condition', field: 'state', op: 'one_of', value: ['WARN', 'CRIT', 'UNKNOWN'] },
          { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
          { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
        ]
      }
    })
  ])
})

test.each([
  {
    canShowMore: true,
    expected: 'Exported 10 of 20 services. Show more services to export more.'
  },
  {
    canShowMore: false,
    expected: 'Exported 10 of 20 services. Narrow the filters to export all of them.'
  }
])(
  'tells how much a truncated export left out (canShowMore: $canShowMore)',
  ({ canShowMore, expected }) => {
    const listing = useServiceListing({})

    expect(listing.exportTexts.truncated({ exported: '10', matched: '20' }, canShowMore)).toBe(
      expected
    )
  }
)
