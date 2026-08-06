/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { emptyService, isMetricSelected, isReadyToCreate } from '@/mode-custom-services/types'

test('isMetricSelected is false until a metric is chosen', () => {
  expect(isMetricSelected(emptyService())).toBe(false)
  expect(isMetricSelected({ ...emptyService(), metricName: 'otel.http.duration' })).toBe(true)
})

describe('isReadyToCreate', () => {
  const ready = { ...emptyService(), serviceName: 'HTTP duration', hostName: 'web01' }

  test('true when both a service name and a host are set', () => {
    expect(isReadyToCreate(ready)).toBe(true)
  })

  test('false when no host is assigned', () => {
    expect(isReadyToCreate({ ...ready, hostName: null })).toBe(false)
    expect(isReadyToCreate({ ...ready, hostName: '   ' })).toBe(false)
  })

  // Regression: clearing the service name must disable "Create & activate changes".
  test('false when the service name is empty or whitespace', () => {
    expect(isReadyToCreate({ ...ready, serviceName: '' })).toBe(false)
    expect(isReadyToCreate({ ...ready, serviceName: '   ' })).toBe(false)
  })
})
