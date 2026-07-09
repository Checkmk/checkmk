/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** A Livestatus filter matching every host whose `name` is one of `hostNames`. */
export function hostNameQuery(hostNames: string[]) {
  return {
    op: 'or' as const,
    expr: hostNames.map((name) => ({ op: '=' as const, left: 'name', right: name }))
  }
}
