/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { labelColor, toLabelItems, toTagItems } from '@/monitoring/shared/labels'

describe('labelColor', () => {
  it('gives a label the colour of the source it was set from', () => {
    expect(labelColor('discovered')).toBe('discovered')
    expect(labelColor('explicit')).toBe('explicit')
    expect(labelColor('ruleset')).toBe('ruleset')
  })

  /** The classic view has no fourth source colour: what is left over is the cyan of a plain tag. */
  it('gives a label whose source says nothing the plain label colour', () => {
    expect(labelColor('unspecified')).toBe('label')
    expect(labelColor('')).toBe('label')
  })
})

describe('toLabelItems', () => {
  it('reads the colour of each label off its source', () => {
    const items = toLabelItems({
      'cmk/check_plugin': { value: 'cpu_load', source: 'discovered' },
      owner: { value: 'platform', source: 'explicit' },
      'cmk/site': { value: 'heute', source: 'ruleset' }
    })

    expect(items.map((item) => [item.text, item.color])).toEqual([
      ['cmk/check_plugin: cpu_load', 'discovered'],
      ['cmk/site: heute', 'ruleset'],
      ['owner: platform', 'explicit']
    ])
  })
})

describe('toTagItems', () => {
  it('leaves every tag in the plain grey a contact group carries', () => {
    expect(toTagItems({ criticality: 'prod', networking: 'lan' })).toEqual([
      { text: 'criticality: prod' },
      { text: 'networking: lan' }
    ])
  })
})
