/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type FolderQuery,
  hostsMatchedByAncestor,
  parseFolderQuery,
  selfMatches,
  serviceMatches,
  serviceVisible,
  subtreeVisible,
  visibleHostStats
} from '@/maps/map/foldertree/filter'
import type { FolderTreeNode } from '@/maps/types/api'

import { aFolderNode } from '../../support/fixtures'

function folder(title: string, children: FolderTreeNode[] = []): FolderTreeNode {
  return aFolderNode({
    path: title,
    title,
    kind: 'folder',
    is_empty: children.length === 0,
    folder_id: title,
    children
  })
}

function host(title: string, state = 'UP'): FolderTreeNode {
  return { ...folder(title), kind: 'host', state, is_empty: false }
}

function service(title: string, state = 'OK'): FolderTreeNode {
  return { ...folder(title), kind: 'service', state, is_empty: false }
}

/** The query a search box in that state produces. */
function query(raw: string, overrides: Partial<FolderQuery> = {}): FolderQuery {
  return {
    terms: parseFolderQuery(raw),
    problemsOnly: false,
    severity: 'any',
    matchedHosts: new Set(),
    ...overrides
  }
}

describe('parseFolderQuery', () => {
  it('keeps only host/service/bare terms (drops hg/sg/id)', () => {
    expect(parseFolderQuery('h:web s:cpu')).toEqual([
      { field: 'host', needle: 'web' },
      { field: 'service', needle: 'cpu' }
    ])
    expect(parseFolderQuery('hg:linux sg:db id:foo')).toEqual([])
    expect(parseFolderQuery('h:web hg:linux')).toEqual([{ field: 'host', needle: 'web' }])
  })

  it('treats bare text as an "any" term', () => {
    expect(parseFolderQuery('datacenter')).toEqual([{ field: 'any', needle: 'datacenter' }])
  })

  it('tolerates whitespace after the operator (CMK parity)', () => {
    expect(parseFolderQuery('h: web')).toEqual([{ field: 'host', needle: 'web' }])
  })
})

describe('serviceMatches', () => {
  it('matches host terms against the host name, service terms against the service', () => {
    expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('h:web'))).toBe(true)
    expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('s:cpu'))).toBe(true)
    expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('s:disk'))).toBe(false)
  })

  it('AND-combines host + service terms', () => {
    const terms = parseFolderQuery('h:web s:cpu')
    expect(serviceMatches('web-01', 'CPU load', terms)).toBe(true)
    expect(serviceMatches('db-01', 'CPU load', terms)).toBe(false)
    expect(serviceMatches('web-01', 'Disk /', terms)).toBe(false)
  })

  it('matches a bare term against either host or service', () => {
    const terms = parseFolderQuery('web')
    expect(serviceMatches('web-01', 'CPU', terms)).toBe(true)
    expect(serviceMatches('db-01', 'web check', terms)).toBe(true)
    expect(serviceMatches('db-01', 'CPU', terms)).toBe(false)
  })
})

describe('selfMatches', () => {
  it('reveals a whole host only for host/bare queries (no service term)', () => {
    expect(selfMatches(host('web-01'), parseFolderQuery('h:web'))).toBe(true)
    expect(selfMatches(host('web-01'), parseFolderQuery('web'))).toBe(true)
    // A service-scoped term must be checked against the leaves, so the host
    // is not a blanket hit.
    expect(selfMatches(host('web-01'), parseFolderQuery('h:web s:cpu'))).toBe(false)
    expect(selfMatches(host('web-01'), parseFolderQuery('s:cpu'))).toBe(false)
  })

  it('matches a folder name only for unscoped queries', () => {
    expect(selfMatches(folder('Datacenters'), parseFolderQuery('datacenter'))).toBe(true)
    expect(selfMatches(folder('Datacenters'), parseFolderQuery('h:data'))).toBe(false)
  })
})

describe('subtreeVisible', () => {
  it('shows hosts matching host/bare terms', () => {
    expect(subtreeVisible(host('web-01'), query('h:web'))).toBe(true)
    expect(subtreeVisible(host('db-01'), query('h:web'))).toBe(false)
  })

  it('narrows a pure service query to the server-matched hosts', () => {
    // No server match (yet) → host hidden, instead of listing the whole site.
    expect(subtreeVisible(host('db-01'), query('s:cpu'))).toBe(false)
    // Server reported a matching service on this host → it shows to drill into.
    expect(
      subtreeVisible(host('db-01'), query('s:cpu', { matchedHosts: new Set(['db-01']) }))
    ).toBe(true)
  })

  it('gates hosts on the server match once a service term is present', () => {
    const matched = query('h:web s:cpu', { matchedHosts: new Set(['web-01']) })
    expect(subtreeVisible(host('web-01'), matched)).toBe(true)
    expect(subtreeVisible(host('db-01'), matched)).toBe(false)
    // Server applies the host term too, so without a match the host is hidden.
    expect(subtreeVisible(host('web-01'), query('h:web s:cpu'))).toBe(false)
  })

  it('keeps instant host-name matches for bare terms, plus server service hits', () => {
    // Bare term matches the host name directly — no server round-trip needed.
    expect(subtreeVisible(host('web-01'), query('web'))).toBe(true)
    // …and a host whose name doesn't match still shows if the server found a
    // matching service on it.
    expect(subtreeVisible(host('db-01'), query('web', { matchedHosts: new Set(['db-01']) }))).toBe(
      true
    )
    expect(subtreeVisible(host('db-01'), query('web'))).toBe(false)
  })

  it('reveals a folder whose name matches an unscoped query', () => {
    const tree = folder('Datacenters', [host('node-1')])
    expect(subtreeVisible(tree, query('datacenter'))).toBe(true)
  })

  it('honours the problems-only toggle on hosts', () => {
    expect(subtreeVisible(host('web-01', 'UP'), query('', { problemsOnly: true }))).toBe(false)
    expect(subtreeVisible(host('web-01', 'DOWN'), query('', { problemsOnly: true }))).toBe(true)
  })
})

describe('serviceVisible', () => {
  it('filters lazily-loaded service leaves with their host in context', () => {
    const scoped = query('h:web s:cpu')
    expect(serviceVisible('web-01', service('CPU load'), scoped)).toBe(true)
    expect(serviceVisible('web-01', service('Disk /'), scoped)).toBe(false)
  })

  it('shows all services once an ancestor (host self-match) matched', () => {
    expect(serviceVisible('web-01', service('Disk /'), query('h:web'), true)).toBe(true)
  })

  it('applies the problems-only toggle', () => {
    const problems = query('', { problemsOnly: true })
    expect(serviceVisible('web-01', service('CPU', 'OK'), problems)).toBe(false)
    expect(serviceVisible('web-01', service('CPU', 'CRITICAL'), problems)).toBe(true)
  })
})

describe('problems severity threshold', () => {
  const problems = (severity: 'any' | 'critical') => query('', { problemsOnly: true, severity })

  it('keeps WARNING hosts with severity "any" but drops them with "critical"', () => {
    expect(subtreeVisible(host('w1', 'WARNING'), problems('any'))).toBe(true)
    expect(subtreeVisible(host('w1', 'WARNING'), problems('critical'))).toBe(false)
    expect(subtreeVisible(host('c1', 'CRITICAL'), problems('critical'))).toBe(true)
  })

  it('treats DOWN/UNREACHABLE as critical, UNKNOWN as soft', () => {
    expect(subtreeVisible(host('d', 'DOWN'), problems('critical'))).toBe(true)
    expect(subtreeVisible(host('u', 'UNREACHABLE'), problems('critical'))).toBe(true)
    expect(subtreeVisible(host('k', 'UNKNOWN'), problems('critical'))).toBe(false)
  })

  it('applies the threshold to lazily-loaded service leaves', () => {
    expect(serviceVisible('h', service('s', 'WARNING'), problems('critical'), false)).toBe(false)
    expect(serviceVisible('h', service('s', 'CRITICAL'), problems('critical'), false)).toBe(true)
  })
})

describe('visibleHostStats', () => {
  const tree = folder('Main', [
    folder('web', [host('web-01', 'UP'), host('web-02', 'DOWN')]),
    folder('db', [host('db-01', 'WARNING')])
  ])

  it('counts every host, and the problems among them, when nothing is filtered', () => {
    expect(visibleHostStats(tree, query(''))).toEqual({
      hosts: 3,
      counts: { DOWN: 1, WARNING: 1 }
    })
  })

  it('counts only what survives the filter, so the summary matches the screen', () => {
    expect(visibleHostStats(tree, query('h:web'))).toEqual({ hosts: 2, counts: { DOWN: 1 } })
    expect(visibleHostStats(tree, query('', { problemsOnly: true }))).toEqual({
      hosts: 2,
      counts: { DOWN: 1, WARNING: 1 }
    })
  })
})

describe('hostsMatchedByAncestor', () => {
  const tree = folder('Main', [
    folder('Datacenters', [host('node-1'), folder('Rack A', [host('node-2')])]),
    folder('Staging', [host('stage-1')])
  ])

  it('collects the hosts a folder name above them revealed, however deep', () => {
    const found = hostsMatchedByAncestor(tree, parseFolderQuery('datacenter'))

    expect([...found]).toEqual(['node-1', 'node-2'])
  })

  it('leaves out hosts whose folders did not match', () => {
    expect(hostsMatchedByAncestor(tree, parseFolderQuery('staging')).has('node-1')).toBe(false)
  })

  it('reports nothing for a host-scoped query, which never matches a folder', () => {
    expect(hostsMatchedByAncestor(tree, parseFolderQuery('h:node'))).toEqual(new Set())
  })

  it('reports nothing when there is no query at all', () => {
    expect(hostsMatchedByAncestor(tree, parseFolderQuery(''))).toEqual(new Set())
  })
})
