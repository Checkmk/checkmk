/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { dummyT, dummyTn, dummyTp, dummyTnp } from '@/lib/i18nDummy'

test('i18n: dummyT function', () => {
  expect(dummyT('Hello')).toBe('Hello')
  expect(dummyT('Hello %{name}!', { name: 'Alice' })).toBe('Hello Alice!')
  expect(dummyT('Hello %{  name  }!', { name: 'Alice' })).toBe('Hello Alice!')
  expect(dummyT('Hello %{name1} and %{name2}!', { name1: 'Alice', name2: 'Bob' })).toBe(
    'Hello Alice and Bob!'
  )
})

test('i18n: dummyTn function', () => {
  expect(dummyTn('apple', 'apples', 1)).toBe('apple')
  expect(dummyTn('apple', 'apples', 2)).toBe('apples')
  expect(dummyTn('%{count} apple', '%{count} apples', 0, { count: 0 })).toBe('0 apples')
  expect(dummyTn('%{count} apple', '%{count} apples', 1, { count: 1 })).toBe('1 apple')
  expect(dummyTn('%{count} apple', '%{count} apples', 2, { count: 2 })).toBe('2 apples')
})

test('i18n: dummyTp function', () => {
  expect(dummyTp('ctx', 'Hello')).toBe('Hello')
  expect(dummyTp('ctx', 'Hello %{name}!', { name: 'Alice' })).toBe('Hello Alice!')
})

test('i18n: dummyTnp function', () => {
  expect(dummyTnp('ctx', 'apple', 'apples', 1)).toBe('apple')
  expect(dummyTnp('ctx', 'apple', 'apples', 2)).toBe('apples')
  expect(dummyTnp('ctx', '%{count} apple', '%{count} apples', 0, { count: 0 })).toBe('0 apples')
  expect(dummyTnp('ctx', '%{count} apple', '%{count} apples', 1, { count: 1 })).toBe('1 apple')
  expect(dummyTnp('ctx', '%{count} apple', '%{count} apples', 2, { count: 2 })).toBe('2 apples')
})
