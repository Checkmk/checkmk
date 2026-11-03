/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface MembersQuery {
  objectTypes: 'host' | 'service'
  objectFilter: string
}

// Line breaks and control bytes: any of them would split a Filter: line.
function isSingleLine(value: string): boolean {
  return ![...value].some((c) => {
    const code = c.codePointAt(0) ?? 0
    return code < 0x20 || code === 0x7f || code === 0x85 || code === 0x2028 || code === 0x2029
  })
}

/**
 * The members of a group without those its ``exclude_members`` pattern leaves
 * out, as a dynamic group's query. ``null`` where the pattern leaves the
 * listed members alone: a host group's ``host~~service`` thins its services
 * only. Mirrors ``excluded_members_filter`` in ``cmk.maps.shared.filters``.
 */
export function groupMembersQuery(
  groupType: 'hostgroup' | 'servicegroup',
  group: string,
  pattern: string
): MembersQuery | null {
  if (!isSingleLine(group) || !isSingleLine(pattern) || `${group}${pattern}`.includes('\\n')) {
    return null
  }
  const [host = '', service] = pattern.split('~~')
  if (groupType === 'hostgroup') {
    if (service !== undefined) {
      return null
    }
    return {
      objectTypes: 'host',
      objectFilter: `Filter: groups >= ${group}\nFilter: name !~~ ${host}\n`
    }
  }
  const lines: string[] = []
  if (host) {
    lines.push(`Filter: host_name !~~ ${host}\n`)
  }
  if (service) {
    lines.push(`Filter: description !~~ ${service}\n`)
  }
  if (lines.length === 2) {
    lines.push('Or: 2\n')
  }
  return { objectTypes: 'service', objectFilter: `Filter: groups >= ${group}\n${lines.join('')}` }
}
