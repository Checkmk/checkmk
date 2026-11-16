/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { vi } from 'vitest'

import FilterTag from '@/monitoring/shared/components/FilterTag.vue'
import {
  MONITORING_SERVICE,
  NARROW_TARGET
} from '@/monitoring/shared/components/MonitoringTableContext'
import { groupCondition } from '@/monitoring/shared/labels'
import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'

import { makeListingService } from '../services/testHelpers'

const ITEM = { text: 'linux' as TranslatedString }

test('links to the page a narrow target names instead of narrowing the listing', async () => {
  const service = makeListingService()
  const target = vi.fn((condition: ColumnCondition) => `hosts.py?${JSON.stringify(condition)}`)
  render(FilterTag, {
    props: { item: ITEM, filterBy: groupCondition },
    global: {
      provide: { [MONITORING_SERVICE as symbol]: service, [NARROW_TARGET as symbol]: target }
    }
  })

  const link = screen.getByRole('link', { name: 'linux' })
  await userEvent.click(link)

  expect(target).toHaveBeenCalledWith({
    type: 'condition',
    field: 'groups',
    op: 'one_of',
    value: ['linux']
  })
  expect(link).toHaveAttribute('href', `hosts.py?${JSON.stringify(target.mock.calls[0]![0])}`)
  expect(link).toHaveAttribute('target', '_top')
  expect(link).toHaveAttribute('title', 'Show hosts with linux')
  expect(service.filterState.value).toBeUndefined()
})

test('is a link with a narrow target even without a listing', () => {
  render(FilterTag, {
    props: { item: ITEM, filterBy: groupCondition },
    global: { provide: { [NARROW_TARGET as symbol]: () => 'hosts.py' } }
  })

  expect(screen.getByRole('link', { name: 'linux' })).toHaveAttribute('href', 'hosts.py')
})

test('stays plain with neither a listing nor a narrow target', () => {
  render(FilterTag, { props: { item: ITEM, filterBy: groupCondition } })

  expect(screen.queryByRole('button', { name: 'linux' })).not.toBeInTheDocument()
})
