/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Hands out per key the record it handed out last while a new one holds the
 * same values. A prop that is a new record each time redraws its component
 * whenever the parent is drawn, though nothing in it changed.
 */
export function stableRecords<Key extends object, Value extends object>(): (
  key: Key,
  value: Value
) => Value {
  const last = new WeakMap<Key, Value>()
  return (key, value) => {
    const before = last.get(key)
    if (before !== undefined && sameValues(before, value)) {
      return before
    }
    last.set(key, value)
    return value
  }
}

/** Whether two records hold the same keys with identical values. */
export function sameValues(a: object, b: object): boolean {
  const before = Object.entries(a)
  return (
    before.length === Object.keys(b).length &&
    before.every(([key, value]) => (b as Record<string, unknown>)[key] === value)
  )
}
