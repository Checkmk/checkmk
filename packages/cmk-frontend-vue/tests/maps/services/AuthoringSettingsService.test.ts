/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import type { AuthoringSettingsApi } from '@/maps/api/authoringSettings'
import {
  AuthoringSettingsService,
  SETTINGS_DEFAULTS
} from '@/maps/services/AuthoringSettingsService'

function serviceWith(api: Pick<AuthoringSettingsApi, 'fetch'>): AuthoringSettingsService {
  return new AuthoringSettingsService(api)
}

describe('AuthoringSettingsService', () => {
  it('renders on the built-in defaults before anything is fetched', () => {
    const service = serviceWith({ fetch: vi.fn() })
    expect(service.settings.value).toEqual(SETTINGS_DEFAULTS)
  })

  it('has no tile source of its own before the site has answered', () => {
    const service = serviceWith({ fetch: vi.fn() })
    expect(service.tiles.value).toBeNull()
  })

  it('adopts the site defaults, including where geo maps fetch their tiles', async () => {
    const tiles = {
      default_url: 'https://tiles.internal/{z}/{x}/{y}.png',
      allowed_sources: ['https://tiles.internal/']
    }
    const service = serviceWith({
      fetch: vi.fn().mockResolvedValue({ settings: { ...SETTINGS_DEFAULTS, icon_size: 64 }, tiles })
    })

    await service.load()

    expect(service.settings.value.icon_size).toBe(64)
    expect(service.tiles.value).toEqual(tiles)
  })

  it('stays usable when the defaults cannot be read', async () => {
    // Refusing to render a map because an icon size could not be read would be
    // worse than rendering it at the built-in size. The warning is part of that
    // behaviour, so it is expected rather than noise.
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const service = serviceWith({ fetch: vi.fn().mockRejectedValue(new Error('403')) })

    await service.load()

    expect(warn).toHaveBeenCalledOnce()

    expect(service.settings.value).toEqual(SETTINGS_DEFAULTS)
  })
})
