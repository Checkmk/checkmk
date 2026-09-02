/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useMapImport } from '@/maps/home/composables/useMapImport'

import { aMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

/** The change event a file input fires, with the fields the composable reads. */
function fileEvent(file: File | null): Event {
  return { target: { files: file ? [file] : [], value: 'sentinel' } } as unknown as Event
}

let services: ReturnType<typeof fakeMapsServices>
let maps: ReturnType<typeof fakeMapsServices>['maps']
let toastError: ReturnType<typeof vi.spyOn>
let toastWarning: ReturnType<typeof vi.spyOn>

function setup() {
  return runWithServices(services, () => useMapImport())
}

beforeEach(() => {
  services = fakeMapsServices()
  maps = services.maps
  vi.spyOn(maps, 'fetchMaps').mockResolvedValue(undefined)
  vi.spyOn(maps, 'importMapJson').mockResolvedValue(undefined)
  vi.mocked(services.apis.mapConfig.parseCfg).mockResolvedValue({
    map: aMap({ name: 'old' }),
    warnings: []
  })
  toastError = vi.spyOn(services.toasts, 'error').mockImplementation(() => {})
  toastWarning = vi.spyOn(services.toasts, 'warning').mockImplementation(() => {})
})

describe('useMapImport', () => {
  it('imports a JSON map and refreshes the list', async () => {
    const api = setup()
    const event = fileEvent(new File(['{"name":"m1","objects":[]}'], 'm1.json'))
    await api.importFile(event)
    expect(maps.importMapJson).toHaveBeenCalledWith({ name: 'm1', objects: [] }, false)
    expect(maps.fetchMaps).toHaveBeenCalledOnce()
    // Always cleared, so re-picking the same file fires another change event.
    expect((event.target as HTMLInputElement).value).toBe('')
  })

  it('reads a legacy .cfg through the GUI parser, then saves the result', async () => {
    const api = setup()
    await api.importFile(fileEvent(new File(['legacy'], 'old.cfg')))
    expect(vi.mocked(services.apis.mapConfig.parseCfg)).toHaveBeenCalledOnce()
    expect(maps.importMapJson).toHaveBeenCalledWith(aMap({ name: 'old' }), false)
  })

  it('does nothing when no file was selected', async () => {
    const api = setup()
    await api.importFile(fileEvent(null))
    expect(maps.importMapJson).not.toHaveBeenCalled()
  })

  it('asks about overwriting when the name is taken, instead of failing', async () => {
    vi.mocked(maps.importMapJson).mockRejectedValueOnce(new Error('Map already exists'))
    const api = setup()
    await api.importFile(fileEvent(new File(['{"name":"dup","objects":[]}'], 'dup.json')))
    expect(api.conflict.value?.name).toBe('dup')
    expect(maps.fetchMaps).not.toHaveBeenCalled()
    expect(toastError).not.toHaveBeenCalled()
  })

  it('overwrites on confirmation and refreshes', async () => {
    vi.mocked(maps.importMapJson).mockRejectedValueOnce(new Error('Map already exists'))
    const api = setup()
    await api.importFile(fileEvent(new File(['{"name":"dup","objects":[]}'], 'dup.json')))
    await api.confirmOverwrite()
    expect(maps.importMapJson).toHaveBeenLastCalledWith({ name: 'dup', objects: [] }, true)
    expect(maps.fetchMaps).toHaveBeenCalledOnce()
    expect(api.conflict.value).toBeNull()
  })

  it('keeps the map when the overwrite question is dismissed', async () => {
    vi.mocked(maps.importMapJson).mockRejectedValueOnce(new Error('Map already exists'))
    const api = setup()
    await api.importFile(fileEvent(new File(['{"name":"dup","objects":[]}'], 'dup.json')))
    api.dismissConflict()
    expect(api.conflict.value).toBeNull()
    expect(maps.importMapJson).toHaveBeenCalledOnce()
  })

  it('surfaces what the .cfg importer had to guess, once the map is stored', async () => {
    // The importer remaps the source installation's monitoring backends onto the
    // connections configured here; silent guesses would leave the operator
    // wondering why an object stays PENDING.
    vi.mocked(services.apis.mapConfig.parseCfg).mockResolvedValue({
      map: aMap({ name: 'old' }),
      warnings: ['Connection was remapped.']
    })
    const api = setup()
    await api.importFile(fileEvent(new File(['legacy'], 'old.cfg')))
    expect(toastWarning).toHaveBeenCalledOnce()
  })

  it('holds the warnings back until an overwrite is actually confirmed', async () => {
    vi.mocked(services.apis.mapConfig.parseCfg).mockResolvedValue({
      map: aMap({ name: 'old' }),
      warnings: ['Connection was remapped.']
    })
    vi.mocked(maps.importMapJson).mockRejectedValueOnce(new Error('Map already exists'))
    const api = setup()
    await api.importFile(fileEvent(new File(['legacy'], 'old.cfg')))
    expect(toastWarning).not.toHaveBeenCalled()

    await api.confirmOverwrite()
    expect(toastWarning).toHaveBeenCalledOnce()
  })

  it('reports a broken file as an error and still clears the input', async () => {
    const api = setup()
    const event = fileEvent(new File(['not json'], 'bad.json'))
    await api.importFile(event)
    expect(toastError).toHaveBeenCalled()
    expect(maps.importMapJson).not.toHaveBeenCalled()
    expect((event.target as HTMLInputElement).value).toBe('')
  })
})
