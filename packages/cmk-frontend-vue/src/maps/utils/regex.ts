/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Compile a user-supplied regex string into a ``RegExp`` object.
 *
 * Centralises the eslint ``security/detect-non-literal-regexp`` rule
 * trade-off: the patterns we deal with come from operator-typed UI
 * fields (BI exclude_members regex, etc.) and only ever run against
 * already-fetched, bounded data on the same client. There's no server
 * round-trip, no unbounded user feed, and ReDoS impact is capped by
 * the test loops the caller writes.
 *
 * Throws ``SyntaxError`` for an invalid pattern — callers are expected
 * to catch and render a "regex invalid" UI hint.
 */
export function compileRegex(pattern: string, flags?: string): RegExp {
  return new RegExp(pattern, flags)
}
