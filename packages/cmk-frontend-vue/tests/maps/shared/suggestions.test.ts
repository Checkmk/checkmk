/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import {
  localSuggestions,
  namedSuggestions,
  suggestionList,
  titledSuggestions
} from '@/maps/shared/suggestions'

describe('namedSuggestions', () => {
  it('offers a name as its own label — the daemon has no titles', () => {
    expect(namedSuggestions(['web01'])).toEqual([{ name: 'web01', title: 'web01' }])
  })
})

describe('titledSuggestions', () => {
  it('falls back to the id when there is no title', () => {
    expect(titledSuggestions([{ id: 'agg-1', title: '' }])).toEqual([
      { name: 'agg-1', title: 'agg-1' }
    ])
  })
})

describe('localSuggestions', () => {
  const hosts = namedSuggestions(['web01', 'web02', 'db-prod'])

  it('matches on the label, case-insensitively', async () => {
    const response = await localSuggestions(() => hosts)('WEB')
    expect(response.choices).toEqual(namedSuggestions(['web01', 'web02']))
  })

  it('matches on the id too, so a value resolves to its own label', async () => {
    // How CmkDropdown asks for the label of the value it holds: the value is
    // the query. Maps, BI aggregations and metrics carry an id that is not
    // their title, so a title-only match would not find their own binding.
    const maps = titledSuggestions([{ id: 'all_hosts', title: 'Host radar' }])
    const response = await localSuggestions(() => maps)('all_hosts')
    expect(response.choices).toEqual([{ name: 'all_hosts', title: 'Host radar' }])
  })

  it('offers everything for an empty query', async () => {
    expect((await localSuggestions(() => hosts)('  ')).choices).toHaveLength(3)
  })

  it('caps how many entries a dropdown has to render at once', async () => {
    const many = namedSuggestions(Array.from({ length: 600 }, (_, i) => `host-${i}`))
    expect((await localSuggestions(() => many)('')).choices).toHaveLength(500)
  })

  it('reads the list on every query, so a later load is picked up', async () => {
    const list = ref(namedSuggestions([]))
    const query = localSuggestions(() => list.value)

    expect((await query('')).choices).toHaveLength(0)
    list.value = hosts
    expect((await query('')).choices).toHaveLength(3)
  })
})

describe('suggestionList', () => {
  it('tracks the caller’s own source', () => {
    const names = ref(['web01'])
    const list = suggestionList(() => namedSuggestions(names.value))

    expect(list.items.value).toHaveLength(1)
    names.value = ['web01', 'web02']
    expect(list.items.value).toHaveLength(2)
    expect(list.loading.value).toBe(false)
  })
})
