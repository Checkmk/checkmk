/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useMapExport } from '@/maps/home/composables/useMapExport'

import { aMap } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

let services: ReturnType<typeof fakeMapsServices>
let click: ReturnType<typeof vi.spyOn>
let created: string[]

beforeEach(() => {
  services = fakeMapsServices()
  vi.spyOn(services.maps, 'getMap').mockResolvedValue(aMap({ name: 'exported' }))
  created = []
  // jsdom implements neither of these; the test only cares that the download is
  // handed to the browser with the map's name on it.
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:map'),
    revokeObjectURL: vi.fn()
  })
  click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement
  ) {
    created.push(this.download)
  })
})

afterEach(() => {
  click.mockRestore()
  vi.unstubAllGlobals()
})

describe('useMapExport', () => {
  it('downloads the map as a JSON file named after it', async () => {
    const { exportMap } = runWithServices(services, () => useMapExport())
    await exportMap('exported')
    expect(services.maps.getMap).toHaveBeenCalledWith('exported')
    expect(created).toEqual(['exported.json'])
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:map')
  })

  it('reports a failed read instead of downloading an empty file', async () => {
    vi.mocked(services.maps.getMap).mockRejectedValueOnce(new Error('gone'))
    const toastError = vi.spyOn(services.toasts, 'error').mockImplementation(() => {})
    const { exportMap } = runWithServices(services, () => useMapExport())
    await exportMap('exported')
    expect(toastError).toHaveBeenCalledWith('gone')
    expect(created).toEqual([])
  })
})
