/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapSearch, { type SearchMatches } from '@/maps/map/components/MapSearch.vue'

import { mapsGlobal } from '../../support/services'

function renderSearch(hits: SearchMatches | undefined, modelValue = 'perf') {
  const steps: (1 | -1)[] = []
  render(MapSearch, {
    props: { modelValue, hits, onStep: (direction: 1 | -1) => steps.push(direction) },
    global: mapsGlobal()
  })
  return { steps, input: screen.getByRole('combobox') }
}

describe('MapSearch', () => {
  it('says how many matches there are', () => {
    renderSearch({ total: 3, reachable: 3, current: null })
    expect(screen.getByText('3 matches')).toBeInTheDocument()
  })

  it('says which match it shows', () => {
    renderSearch({ total: 3, reachable: 3, current: 1 })
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
  })

  it('says when nothing matches', () => {
    renderSearch({ total: 0, reachable: 0, current: null })
    expect(screen.getByText('No matches')).toBeInTheDocument()
  })

  it('says nothing about matches without a search', () => {
    renderSearch({ total: 0, reachable: 0, current: null }, '')
    expect(screen.queryByText('No matches')).toBeNull()
  })

  it('steps to the next match on Enter and back on Shift+Enter', async () => {
    const { steps, input } = renderSearch({ total: 3, reachable: 3, current: null })
    await fireEvent.keyDown(input, { key: 'Enter' })
    await fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(steps).toEqual([1, -1])
  })

  it('does not step through more matches than the map can show', async () => {
    const { steps, input } = renderSearch({ total: 2000, reachable: 120, current: null })
    await fireEvent.keyDown(input, { key: 'Enter' })
    expect(steps).toEqual([])
    expect(screen.getByText('2000 matches')).toBeInTheDocument()
  })

  it('searches nothing while a leading slash calls up the operators', async () => {
    const searched: string[] = []
    render(MapSearch, {
      props: { modelValue: 'perf', 'onUpdate:modelValue': (value: string) => searched.push(value) },
      global: mapsGlobal()
    })
    const input = screen.getByRole('combobox')
    await fireEvent.update(input, '/')
    await fireEvent.update(input, '/perf')
    await fireEvent.keyDown(input, { key: 'ArrowDown' })
    await fireEvent.keyDown(input, { key: 'Enter' })
    expect(searched.filter((value) => value.includes('/'))).toEqual([])
    expect(searched.at(-1)).toBe('h:perf')
  })
})
