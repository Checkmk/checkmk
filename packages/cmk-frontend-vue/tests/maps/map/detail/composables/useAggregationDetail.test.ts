/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useAggregationDetail } from '@/maps/map/detail/composables/useAggregationDetail'

import { aState, anAggregationNode, anObject } from '../../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../../support/services'

describe('useAggregationDetail', () => {
  it('names an unknown leaf as the worst over a warning one, as BI ranks them', () => {
    const tree = anAggregationNode({
      name: 'Shop',
      node_type: 'bi_aggregator',
      state: 3,
      children: [
        anAggregationNode({ name: 'Disk', node_type: 'bi_leaf', state: 1, output: 'disk' }),
        anAggregationNode({ name: 'Agent', node_type: 'bi_leaf', state: 3, output: 'agent' })
      ]
    })
    const detail = runWithServices(fakeMapsServices(), () =>
      useAggregationDetail({
        object: () => anObject({ id: 'a', type: 'aggregation' }),
        state: () => aState({ object_id: 'a', type: 'aggregation', state: 'UNKNOWN', tree }),
        checkmkUrl: () => null,
        connectionId: () => null,
        onSelectHost: () => {},
        onBulkAcknowledge: () => {}
      })
    )

    expect(detail.aggregationSummary.value?.worstOutput).toBe('agent')
  })
})
