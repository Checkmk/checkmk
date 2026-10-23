/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useMapClone } from '@/maps/home/composables/useMapClone'
import type { MapRead } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

let services: ReturnType<typeof fakeMapsServices>
let maps: ReturnType<typeof fakeMapsServices>['maps']

function setup() {
  return runWithServices(services, () => useMapClone())
}

function cloneSource(over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name: 'prod', alias: 'Production', ...over })
}

beforeEach(() => {
  services = fakeMapsServices()
  maps = services.maps
  vi.spyOn(maps, 'cloneMap').mockResolvedValue(undefined)
})

describe('useMapClone', () => {
  it('proposes "_copy" as the id and marks the alias as a copy', () => {
    const clone = setup()
    clone.start(cloneSource())
    expect(clone.source.value).toBe('prod')
    expect(clone.name.value).toBe('prod_copy')
    expect(clone.alias.value).toBe('Production (Copy)')
  })

  it('leaves the alias empty when the source has none', () => {
    const clone = setup()
    clone.start(cloneSource({ alias: '' }))
    expect(clone.alias.value).toBe('')
  })

  it('sanitizes what is typed into the id', () => {
    const clone = setup()
    clone.setName('My Map!')
    expect(clone.name.value).not.toMatch(/[ !]/)
  })

  it('clones with the chosen id and alias, then closes', async () => {
    const clone = setup()
    clone.start(cloneSource())
    await clone.clone()
    expect(maps.cloneMap).toHaveBeenCalledWith('prod', 'prod_copy', 'Production (Copy)')
    expect(clone.source.value).toBeNull()
  })

  it('omits an empty alias so the server keeps its own default', async () => {
    const clone = setup()
    clone.start(cloneSource({ alias: '' }))
    await clone.clone()
    expect(maps.cloneMap).toHaveBeenCalledWith('prod', 'prod_copy', undefined)
  })

  it('keeps the dialog open and shows why a clone failed', async () => {
    vi.mocked(maps.cloneMap).mockRejectedValueOnce(new Error('name taken'))
    const clone = setup()
    clone.start(cloneSource())
    await clone.clone()
    expect(clone.error.value).toBe('name taken')
    expect(clone.source.value).toBe('prod')
  })

  it('does not clone without an id', async () => {
    const clone = setup()
    clone.start(cloneSource())
    clone.setName('')
    await clone.clone()
    expect(maps.cloneMap).not.toHaveBeenCalled()
  })
})
