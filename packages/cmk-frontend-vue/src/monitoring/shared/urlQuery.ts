/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Characters {@link encodeQueryValue} leaves untouched. Narrower than
 * `encodeURIComponent`'s own safe set: a raw `'` makes a URL unbookmarkable
 * (`BookmarkList.validate_url` -> `is_allowed_url` -> `URL_CHAR_REGEX`,
 * `packages/cmk-ccc/cmk/ccc/regex.py`), and `,`/`:`/`;` stay readable
 * because this module's own values use them as separators.
 */
const SAFE_CHAR = /[A-Za-z0-9\-._~,;:]/

/** Characters `encodeURIComponent` leaves unescaped that ours must not. */
const FORCE_ESCAPE: Readonly<Record<string, string>> = {
  "'": '%27',
  '!': '%21',
  '*': '%2A',
  '(': '%28',
  ')': '%29'
}

/** Percent-encodes everything outside {@link SAFE_CHAR}; space becomes `%20`. */
export function encodeQueryValue(value: string): string {
  return Array.from(value)
    .map((char) => (SAFE_CHAR.test(char) ? char : (FORCE_ESCAPE[char] ?? encodeURIComponent(char))))
    .join('')
}

interface QuerySegment {
  /** Decoded key, for matching against owned keys. */
  key: string
  /** The original `key` or `key=value` text, byte-for-byte. */
  raw: string
}

function decodeKey(raw: string): string {
  const separator = raw.indexOf('=')
  const key = separator === -1 ? raw : raw.slice(0, separator)
  try {
    return decodeURIComponent(key.replace(/\+/g, ' '))
  } catch {
    return key
  }
}

/** Splits a `?`-prefixed or bare query string into segments, keeping each one's raw text intact. */
export function parseQuery(search: string): QuerySegment[] {
  const trimmed = search.startsWith('?') ? search.slice(1) : search
  if (trimmed === '') {
    return []
  }
  return trimmed.split('&').map((raw) => ({ key: decodeKey(raw), raw }))
}

/**
 * Merges `updates` into `search`, touching only the keys `updates` names.
 * Every other param survives untouched - same value, same relative order,
 * same raw encoding - which is what lets a dashboard link keep its filter
 * vars across every write this table makes.
 */
export function mergeQuery(search: string, updates: Record<string, string | null>): string {
  const owned = new Set(Object.keys(updates))
  const kept = parseQuery(search)
    .filter((segment) => !owned.has(segment.key))
    .map((segment) => segment.raw)
  const written = Object.entries(updates)
    .filter((entry): entry is [string, string] => entry[1] !== null)
    .map(([key, value]) => `${key}=${encodeQueryValue(value)}`)
  const combined = [...kept, ...written]
  return combined.length > 0 ? `?${combined.join('&')}` : ''
}
