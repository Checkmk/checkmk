/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { isAutoLoadable, isEmbeddableGraphUrl } from '@/maps/utils/autoLoadUrl'

describe('isAutoLoadable', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function servedAt(href: string): void {
    vi.stubGlobal('location', new URL(href))
  }

  it('refuses a page of the site', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('logout.py')).toBe(false)
    expect(isAutoLoadable('http://mon.example/heute/check_mk/logout.py')).toBe(false)
  })

  it('refuses a page of the site under another scheme or port', () => {
    servedAt('https://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('http://mon.example/heute/check_mk/logout.py')).toBe(false)
    expect(isAutoLoadable('https://mon.example:8443/heute/check_mk/logout.py')).toBe(false)
  })

  it('refuses a path that leaves the asset directory again', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('maps/images/../../logout.py')).toBe(false)
  })

  it('allows the Maps image directory', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('http://mon.example/heute/check_mk/maps/images/rack.png')).toBe(true)
  })

  it('refuses the rest of the Maps path', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('maps/api/v1/sse/maps/floor?tab=t')).toBe(false)
    expect(isAutoLoadable('maps/backgrounds/0123456789abcdef__floor.png')).toBe(false)
  })

  it('allows another server', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('https://tiles.example/1/2/3.png')).toBe(true)
  })

  it('refuses a scheme other than http and https', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(isAutoLoadable('javascript:alert(1)')).toBe(false)
  })
})

describe('isEmbeddableGraphUrl', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('allows the read-only graph, view and dashboard pages of the site', () => {
    vi.stubGlobal('location', new URL('http://mon.example/heute/check_mk/maps.py'))
    expect(isEmbeddableGraphUrl('view.py?view_name=allhosts')).toBe(true)
    expect(isEmbeddableGraphUrl('/heute/check_mk/graph_image.py?request=x')).toBe(true)
    expect(isEmbeddableGraphUrl('dashboard.py?name=main')).toBe(true)
  })

  it('refuses any other page of the site', () => {
    vi.stubGlobal('location', new URL('http://mon.example/heute/check_mk/maps.py'))
    expect(isEmbeddableGraphUrl('logout.py')).toBe(false)
  })
})
