/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { isInteger } from '@/form/components/utils/validation'

test.each([
  [1, true],
  ['asd', false],
  ['10', false],
  [1000000000000000000000, true], // this was a problem previously
  // some suprising values:
  [5.0, true],
  [5.000000000000001, false],
  // eslint-disable-next-line no-loss-of-precision
  [5.0000000000000001, true],
  // eslint-disable-next-line no-loss-of-precision
  [4500000000000000.1, true]
])('isInteger(%s, %s)', (value, expected) => {
  expect(isInteger(value)).toBe(expected)
})
