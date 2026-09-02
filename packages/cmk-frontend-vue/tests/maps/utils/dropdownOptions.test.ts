/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { beforeEach, describe, expect, it } from 'vitest'

import {
  linePerfdataLabelOptions,
  lineStyleOptions,
  mapTypeOptions,
  placeableObjectTypes
} from '@/maps/utils/dropdownOptions'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const t: TranslateFn = (msg) => untranslated(msg)

describe('placeableObjectTypes', () => {
  it('lists all object types including graph', () => {
    const names = placeableObjectTypes(t).map((o) => o.name)
    expect(names).toContain('graph')
    expect(names).toContain('host')
    expect(names).toContain('line')
  })
})

describe('mapTypeOptions', () => {
  it('returns all map types unconditionally', () => {
    const names = mapTypeOptions(t).map((o) => o.name)
    expect(names).toEqual(['static', 'worldmap', 'flow', 'radar', 'foldertree', 'presentation'])
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
