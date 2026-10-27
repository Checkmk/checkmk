/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useServiceListing } from '@/monitoring/shared/services/useServiceListing'

test('offers rescheduling and a selection when the user may reschedule', () => {
  const listing = useServiceListing({
    actions: [{ ident: 'reschedule', title: 'Reschedule', icon: 'reload' }]
  })

  expect(listing.permittedActions.map((action) => action.id)).toEqual(['reschedule'])
  expect(listing.mayReschedule).toBe(true)
  expect(listing.mayActOnSelection).toBe(true)
})

test('offers neither rescheduling nor a selection without permitted actions', () => {
  const listing = useServiceListing({})

  expect(listing.permittedActions).toEqual([])
  expect(listing.mayReschedule).toBe(false)
  expect(listing.mayActOnSelection).toBe(false)
})

test('labels a selection of services', () => {
  const listing = useServiceListing({})

  expect(listing.selectionLabel(2)).toBe('Selected services: 2')
  expect(listing.countsLabel(1, 5)).toBe('Selected service: 1 | Total services: 5')
})

test('offers acknowledging, rescheduling, downtimes, comments and notifications for services', () => {
  const listing = useServiceListing({})

  expect(Object.keys(listing.registry)).toEqual([
    'acknowledge',
    'reschedule',
    'schedule_downtimes',
    'add_comment',
    'send_custom_notification'
  ])
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
