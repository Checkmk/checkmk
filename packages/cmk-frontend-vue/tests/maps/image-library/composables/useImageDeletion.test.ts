/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useImageDeletion } from '@/maps/image-library/composables/useImageDeletion'
import type { ImageUsageEntry } from '@/maps/types/api'

import { fakeMapsServices, runWithServices } from '../../support/services'

function usedBy(map: string): ImageUsageEntry {
  return { map, alias: map, is_background: true, object_ids: [] }
}

let services: ReturnType<typeof fakeMapsServices>
let deleted: string[]
let errors: unknown[]

function setup() {
  return runWithServices(services, () =>
    useImageDeletion(
      (name) => deleted.push(name),
      (error) => errors.push(error)
    )
  )
}

beforeEach(() => {
  services = fakeMapsServices()
  deleted = []
  errors = []
  vi.mocked(services.apis.images.usage).mockResolvedValue([])
  vi.mocked(services.apis.images.delete).mockResolvedValue([])
})

describe('useImageDeletion — asking', () => {
  it('asks nothing before it knows whether the image is used', async () => {
    let resolveUsage = (_: ImageUsageEntry[]): void => {}
    vi.mocked(services.apis.images.usage).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveUsage = resolve
      })
    )
    const deletion = setup()
    const started = deletion.start('logo.svg')
    expect(deletion.askedAboutUnused.value).toBe(false)
    expect(deletion.askedAboutUsed.value).toBe(false)

    resolveUsage([])
    await started
    expect(deletion.askedAboutUnused.value).toBe(true)
  })

  it('warns about the maps using the image instead of just asking', async () => {
    vi.mocked(services.apis.images.usage).mockResolvedValueOnce([usedBy('prod')])
    const deletion = setup()
    await deletion.start('logo.svg')
    expect(deletion.askedAboutUsed.value).toBe(true)
    expect(deletion.askedAboutUnused.value).toBe(false)
    expect(deletion.usage.value).toEqual([usedBy('prod')])
  })

  it('falls back to the plain question when the usage check fails', async () => {
    vi.mocked(services.apis.images.usage).mockRejectedValueOnce(new Error('offline'))
    const deletion = setup()
    await deletion.start('logo.svg')
    expect(deletion.askedAboutUnused.value).toBe(true)
  })

  it('ignores a check that answers after another image was clicked', async () => {
    let resolveFirst = (_: ImageUsageEntry[]): void => {}
    vi.mocked(services.apis.images.usage).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      })
    )
    const deletion = setup()
    const first = deletion.start('first.svg')
    await deletion.start('second.svg')

    resolveFirst([usedBy('prod')])
    await first
    expect(deletion.target.value).toBe('second.svg')
    expect(deletion.usage.value).toEqual([])
  })
})

describe('useImageDeletion — deleting', () => {
  it('deletes an unused image and reports it gone', async () => {
    const deletion = setup()
    await deletion.start('logo.svg')
    await deletion.confirm()
    expect(services.apis.images.delete).toHaveBeenCalledWith('logo.svg', false)
    expect(deleted).toEqual(['logo.svg'])
    expect(deletion.target.value).toBeNull()
  })

  it('forces the delete the operator confirmed through the in-use warning', async () => {
    vi.mocked(services.apis.images.usage).mockResolvedValueOnce([usedBy('prod')])
    const deletion = setup()
    await deletion.start('logo.svg')
    await deletion.confirm()
    expect(services.apis.images.delete).toHaveBeenCalledWith('logo.svg', true)
    expect(deleted).toEqual(['logo.svg'])
  })

  it('shows usage the server found and this did not, instead of deleting', async () => {
    vi.mocked(services.apis.images.delete).mockResolvedValueOnce([usedBy('lab')])
    const deletion = setup()
    await deletion.start('logo.svg')
    await deletion.confirm()
    expect(deleted).toEqual([])
    expect(deletion.askedAboutUsed.value).toBe(true)
    expect(deletion.usage.value).toEqual([usedBy('lab')])
  })

  it('reports a failed delete and closes the question', async () => {
    vi.mocked(services.apis.images.delete).mockRejectedValueOnce(new Error('read-only'))
    const deletion = setup()
    await deletion.start('logo.svg')
    await deletion.confirm()
    expect(errors).toHaveLength(1)
    expect(deletion.target.value).toBeNull()
  })

  it('deletes nothing after the question was dismissed', async () => {
    const deletion = setup()
    await deletion.start('logo.svg')
    deletion.cancel()
    await deletion.confirm()
    expect(services.apis.images.delete).not.toHaveBeenCalled()
  })
})
