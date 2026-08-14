/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { middleTruncate } from '@/graphing/utils/middleWordTruncation'

// A fit predicate that treats a fixed character budget as "the available width".
const fitsWithin = (maxChars: number) => (candidate: string) => candidate.length <= maxChars

test('keeps the original text when it already fits', () => {
  expect(middleTruncate('CPU load', () => true)).toBe('CPU load')
})

test('drops whole middle words, keeping head and tail around a spaced ellipsis', () => {
  expect(middleTruncate('alpha beta gamma delta epsilon', fitsWithin(20))).toBe(
    'alpha beta … epsilon'
  )
})

test('collapses irregular whitespace between the kept words', () => {
  expect(middleTruncate('a  b  c  d  e', fitsWithin(5))).toBe('a … e')
})

test('falls back to a character split for a single over-long word', () => {
  const text = middleTruncate('supercalifragilistic', fitsWithin(10))
  expect(text).toContain('…')
  expect(text).not.toContain(' ')
  expect(text.length).toBeLessThanOrEqual(10)
  expect(text.startsWith('s')).toBe(true)
  expect(text.endsWith('c')).toBe(true)
})

test('shrinks to the bare ellipsis when nothing fits', () => {
  expect(middleTruncate('alpha beta gamma', () => false)).toBe('…')
})
