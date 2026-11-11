/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import { groupCondition } from '@/monitoring/shared/labels'

import { makeListingService } from '../../services/testHelpers'

const ITEMS = [{ text: 'linux' as TranslatedString }]

test('narrows the listing to what an entry clicked on names', async () => {
  const service = makeListingService()
  render(OverviewChips, {
    props: { items: ITEMS, filterBy: groupCondition },
    global: { provide: { [MONITORING_SERVICE as symbol]: service } }
  })

  await userEvent.click(screen.getByRole('button', { name: 'linux' }))

  expect(service.filterState.value).toStrictEqual({
    type: 'condition',
    field: 'groups',
    op: 'one_of',
    value: ['linux']
  })
})

test('keeps the entries plain without a filter to narrow by', () => {
  render(OverviewChips, {
    props: { items: ITEMS },
    global: { provide: { [MONITORING_SERVICE as symbol]: makeListingService() } }
  })

  expect(screen.queryByRole('button', { name: 'linux' })).not.toBeInTheDocument()
})
