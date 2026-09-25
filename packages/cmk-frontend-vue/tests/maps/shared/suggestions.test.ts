/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { localSuggestions, suggestionList, titledSuggestions } from '@/maps/shared/suggestions'

describe('titledSuggestions', () => {
  it('falls back to the id when there is no title', () => {
    expect(titledSuggestions([{ id: 'agg-1', title: '' }])).toEqual([
      { name: 'agg-1', title: 'agg-1' }
    ])
  })
})

describe('localSuggestions', () => {
  const metrics = titledSuggestions([
    { id: 'load1', title: 'CPU load 1 min' },
    { id: 'load5', title: 'CPU load 5 min' },
    { id: 'mem_used', title: 'Memory used' }
  ])

  it('matches on the label, case-insensitively', async () => {
    const response = await localSuggestions(() => metrics)('cpu LOAD')
    expect(response.choices).toEqual(metrics.slice(0, 2))
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
    expect((await localSuggestions(() => metrics)('  ')).choices).toHaveLength(3)
  })

  it('caps how many entries a dropdown has to render at once', async () => {
    const many = titledSuggestions(
      Array.from({ length: 600 }, (_, i) => ({ id: `m${i}`, title: `Metric ${i}` }))
    )
    expect((await localSuggestions(() => many)('')).choices).toHaveLength(500)
  })

  it('reads the list on every query, so a later load is picked up', async () => {
    const list = ref(titledSuggestions([]))
    const query = localSuggestions(() => list.value)

    expect((await query('')).choices).toHaveLength(0)
    list.value = metrics
    expect((await query('')).choices).toHaveLength(3)
  })
})

describe('suggestionList', () => {
  it('tracks the caller’s own source', () => {
    const entries = ref([{ id: 'aggr-web', title: 'Web shop' }])
    const list = suggestionList(() => titledSuggestions(entries.value))

    expect(list.items.value).toHaveLength(1)
    entries.value = [...entries.value, { id: 'aggr-mail', title: 'Mail' }]
    expect(list.items.value).toHaveLength(2)
    expect(list.loading.value).toBe(false)
  })
})
