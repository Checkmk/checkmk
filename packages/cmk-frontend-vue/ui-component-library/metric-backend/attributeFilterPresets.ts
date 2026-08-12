/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeFilterModel } from '@/metric-backend/attribute-filter/types'

export type PresetName = 'empty' | 'individual' | 'groupsWithExtra' | 'singleGroup'

export const presetOptions: Array<{ title: string; name: PresetName }> = [
  { title: 'Empty', name: 'empty' },
  { title: '3 individual pills', name: 'individual' },
  { title: '2 groups of 3 + 1 extra pill', name: 'groupsWithExtra' },
  { title: '1 group of 5 pills', name: 'singleGroup' }
]

export const filterPresets: Record<PresetName, AttributeFilterModel> = {
  empty: [],
  individual: [
    {
      id: 'individual-g1',
      conditions: [
        {
          id: 'individual-1',
          attributeKind: 'resource',
          key: 'service.name',
          operator: 'equals',
          value: 'frontend'
        }
      ]
    },
    {
      id: 'individual-g2',
      conditions: [
        {
          id: 'individual-2',
          attributeKind: 'data_point',
          key: 'http.method',
          operator: 'equals',
          value: 'GET'
        }
      ]
    },
    {
      id: 'individual-g3',
      conditions: [
        {
          id: 'individual-3',
          attributeKind: 'data_point',
          key: 'http.status_code',
          operator: 'equals',
          value: '200'
        }
      ]
    }
  ],
  groupsWithExtra: [
    {
      id: 'gx-g1',
      conditions: [
        {
          id: 'gx-g1-a',
          attributeKind: 'resource',
          key: 'service.name',
          operator: 'equals',
          value: 'frontend'
        },
        {
          id: 'gx-g1-b',
          attributeKind: 'data_point',
          key: 'http.method',
          operator: 'equals',
          value: 'GET'
        },
        {
          id: 'gx-g1-c',
          attributeKind: 'data_point',
          key: 'http.status_code',
          operator: 'equals',
          value: '200'
        }
      ]
    },
    {
      id: 'gx-g2',
      conditions: [
        {
          id: 'gx-g2-a',
          attributeKind: 'resource',
          key: 'service.name',
          operator: 'equals',
          value: 'checkout'
        },
        {
          id: 'gx-g2-b',
          attributeKind: 'data_point',
          key: 'http.method',
          operator: 'equals',
          value: 'POST'
        },
        {
          id: 'gx-g2-c',
          attributeKind: 'data_point',
          key: 'http.status_code',
          operator: 'equals',
          value: '500'
        }
      ]
    },
    {
      id: 'gx-g3',
      conditions: [
        {
          id: 'gx-extra',
          attributeKind: 'resource',
          key: 'host.name',
          operator: 'contains',
          value: 'prod'
        }
      ]
    }
  ],
  singleGroup: [
    {
      id: 'single-g',
      conditions: [
        {
          id: 'single-1',
          attributeKind: 'resource',
          key: 'service.name',
          operator: 'equals',
          value: 'frontend'
        },
        {
          id: 'single-2',
          attributeKind: 'resource',
          key: 'deployment.environment',
          operator: 'equals',
          value: 'production'
        },
        {
          id: 'single-3',
          attributeKind: 'data_point',
          key: 'http.method',
          operator: 'equals',
          value: 'GET'
        },
        {
          id: 'single-4',
          attributeKind: 'data_point',
          key: 'http.route',
          operator: 'starts_with',
          value: '/api'
        },
        {
          id: 'single-5',
          attributeKind: 'data_point',
          key: 'http.status_code',
          operator: 'equals',
          value: '200'
        }
      ]
    }
  ]
}
