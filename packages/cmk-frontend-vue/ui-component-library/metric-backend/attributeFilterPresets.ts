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
      id: 'individual-1',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'frontend',
      connector: null
    },
    {
      id: 'individual-2',
      attributeType: 'datapoint',
      key: 'http.method',
      operator: 'eq',
      value: 'GET',
      connector: 'OR'
    },
    {
      id: 'individual-3',
      attributeType: 'datapoint',
      key: 'http.status_code',
      operator: 'eq',
      value: '200',
      connector: 'OR'
    }
  ],
  groupsWithExtra: [
    {
      id: 'gx-g1-a',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'frontend',
      connector: null
    },
    {
      id: 'gx-g1-b',
      attributeType: 'datapoint',
      key: 'http.method',
      operator: 'eq',
      value: 'GET',
      connector: 'AND'
    },
    {
      id: 'gx-g1-c',
      attributeType: 'datapoint',
      key: 'http.status_code',
      operator: 'eq',
      value: '200',
      connector: 'AND'
    },
    {
      id: 'gx-g2-a',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'checkout',
      connector: 'OR'
    },
    {
      id: 'gx-g2-b',
      attributeType: 'datapoint',
      key: 'http.method',
      operator: 'eq',
      value: 'POST',
      connector: 'AND'
    },
    {
      id: 'gx-g2-c',
      attributeType: 'datapoint',
      key: 'http.status_code',
      operator: 'eq',
      value: '500',
      connector: 'AND'
    },
    {
      id: 'gx-extra',
      attributeType: 'resource',
      key: 'host.name',
      operator: 'contains',
      value: 'prod',
      connector: 'OR'
    }
  ],
  singleGroup: [
    {
      id: 'single-1',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'frontend',
      connector: null
    },
    {
      id: 'single-2',
      attributeType: 'resource',
      key: 'deployment.environment',
      operator: 'eq',
      value: 'production',
      connector: 'AND'
    },
    {
      id: 'single-3',
      attributeType: 'datapoint',
      key: 'http.method',
      operator: 'eq',
      value: 'GET',
      connector: 'AND'
    },
    {
      id: 'single-4',
      attributeType: 'datapoint',
      key: 'http.route',
      operator: 'starts_with',
      value: '/api',
      connector: 'AND'
    },
    {
      id: 'single-5',
      attributeType: 'datapoint',
      key: 'http.status_code',
      operator: 'eq',
      value: '200',
      connector: 'AND'
    }
  ]
}
