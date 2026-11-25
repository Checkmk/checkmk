/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { beforeEach, describe, expect, it } from 'vitest'

import type { MapElement } from '@/maps/types/api'
import {
  gridsDeletedAlong,
  linePerfdataLabelOptions,
  lineStyleOptions,
  mapTypeOptions,
  objectDeleteTitle,
  objectDeletedText,
  placeableObjectTypes
} from '@/maps/utils/dropdownOptions'

import { anObject } from '../support/fixtures'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const t: TranslateFn = (msg) => untranslated(msg)

const member = (name: string): MapElement =>
  anObject({ id: `auto:grid:g:${name}`, type: 'host', host_name: name, grid_id: 'g' })

describe('objectDeleteTitle', () => {
  it('asks about a grid by what leaves the map with it', () => {
    const grid = anObject({ id: 'g', type: 'grid', object_types: 'service' })

    expect(objectDeleteTitle(grid, usei18n(), [grid, member('a'), member('b')])).toBe(
      'Delete the grid of 2 services?'
    )
  })

  it('asks about a grid that shows nothing yet by its type', () => {
    const grid = anObject({ id: 'g', type: 'grid' })

    expect(objectDeleteTitle(grid, usei18n(), [grid])).toBe('Delete Grid?')
  })

  it('asks about a host by its name', () => {
    const host = anObject({ id: 'h', type: 'host', host_name: 'web01' })

    expect(objectDeleteTitle(host, usei18n(), [host])).toBe('Delete Host "web01"?')
  })
})

describe('objectDeletedText', () => {
  it('tells what left the map with a grid', () => {
    const grid = anObject({ id: 'g', type: 'grid', object_types: 'host' })

    expect(objectDeletedText(grid, usei18n(), [grid, member('a')])).toBe(
      'Deleted the grid of 1 host'
    )
  })
})

describe('gridsDeletedAlong', () => {
  it('counts what the grids among the deleted objects show', () => {
    const grid = anObject({ id: 'g', type: 'grid' })
    const host = anObject({ id: 'h', type: 'host', host_name: 'web01' })

    expect(gridsDeletedAlong([grid, host], usei18n(), [grid, host, member('a'), member('b')])).toBe(
      'The 2 objects shown by grids among them go too.'
    )
  })

  it('has nothing to add where no grid shows anything', () => {
    const grid = anObject({ id: 'g', type: 'grid' })
    const host = anObject({ id: 'h', type: 'host', host_name: 'web01' })

    expect(gridsDeletedAlong([grid, host], usei18n(), [grid, host])).toBeUndefined()
  })
})

describe('placeableObjectTypes', () => {
  it('lists all object types including graph', () => {
    const names = placeableObjectTypes(t, true).map((o) => o.name)
    expect(names).toContain('graph')
    expect(names).toContain('host')
    expect(names).toContain('line')
    expect(names).toContain('grid')
  })

  it('leaves out the grid where the map takes none', () => {
    expect(placeableObjectTypes(t, false).map((o) => o.name)).not.toContain('grid')
  })
})

describe('mapTypeOptions', () => {
  it('returns all map types unconditionally', () => {
    const names = mapTypeOptions(t).map((o) => o.name)
    expect(names).toEqual(['static', 'geo', 'flow', 'radar', 'foldertree', 'presentation'])
  })
})

describe('linePerfdataLabelOptions', () => {
  it('lists the four perfdata label modes', () => {
    expect(linePerfdataLabelOptions(t).map((o) => o.name)).toEqual([
      'none',
      'percent',
      'bandwidth',
      'both'
    ])
  })
})

describe('lineStyleOptions', () => {
  beforeEach(() => {})

  it('prepends a null Default option and falls back to the built-in styles', () => {
    const options = lineStyleOptions(t)
    expect(options[0]).toEqual({ name: null, title: 'Default' })
    const names = options.map((o) => o.name)
    expect(names).toContain('plain')
    expect(names).toContain('arrow_inward')
  })
})
