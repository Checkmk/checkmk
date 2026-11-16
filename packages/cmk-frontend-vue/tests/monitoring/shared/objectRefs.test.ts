/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'
import { refKey } from '@/monitoring/shared/objectRefs'

function host(site: string, name: string): HostRef {
  return { site_id: site, name }
}

function service(site: string, hostName: string, description: string): ServiceRef {
  return { host: host(site, hostName), description }
}

test('keys two references to the same host alike', () => {
  expect(refKey(host('local', 'web-1'))).toBe(refKey(host('local', 'web-1')))
})

test('keys hosts of the same name on two sites apart', () => {
  expect(refKey(host('local', 'web-1'))).not.toBe(refKey(host('remote', 'web-1')))
})

test('keys two references to the same service alike', () => {
  expect(refKey(service('local', 'web-1', 'CPU load'))).toBe(
    refKey(service('local', 'web-1', 'CPU load'))
  )
})

test('keys services of the same name on two hosts apart', () => {
  expect(refKey(service('local', 'web-1', 'CPU load'))).not.toBe(
    refKey(service('local', 'web-2', 'CPU load'))
  )
})

test('keys a service apart from its host', () => {
  expect(refKey(service('local', 'web-1', 'CPU load'))).not.toBe(refKey(host('local', 'web-1')))
})
