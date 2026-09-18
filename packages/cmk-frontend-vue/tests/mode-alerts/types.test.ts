/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { alertName, emptyAlert, hasUnparsableRegex, servicePattern } from '@/mode-alerts/types'

test('a broken regular expression is reported as unparsable', () => {
  expect(hasUnparsableRegex({ ...emptyAlert(), matchType: 'regex', servicePattern: '[' })).toBe(
    true
  )
})

test('a valid regular expression is accepted', () => {
  expect(
    hasUnparsableRegex({ ...emptyAlert(), matchType: 'regex', servicePattern: 'HTTP.*duration' })
  ).toBe(false)
})

test('a name that is not a regular expression is never reported as unparsable', () => {
  expect(hasUnparsableRegex({ ...emptyAlert(), matchType: 'exact', servicePattern: '[' })).toBe(
    false
  )
})

test('surrounding whitespace is not part of the alert name', () => {
  expect(alertName({ ...emptyAlert(), name: '  Latency too high  ' })).toBe('Latency too high')
})

test('surrounding whitespace is not part of the service name', () => {
  expect(servicePattern({ ...emptyAlert(), servicePattern: '  HTTP  ' })).toBe('HTTP')
})

test('a name of only whitespace counts as no name', () => {
  expect(alertName({ ...emptyAlert(), name: '   ' })).toBe('')
})
