/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import type { MapElement } from '@/maps/types/api'
import { objectAriaLabel, stateAriaLabel } from '@/maps/utils/objectAria'

import { anObject } from '../support/fixtures'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const _t = ((msg: string) => msg) as TranslateFn

const base = { id: 'obj-1', x: 0, y: 0, url_target: '_blank' }

describe('objectAriaLabel', () => {
  it('names monitored objects with their identifier and state', () => {
    const host: MapElement = anObject({ ...base, type: 'host', host_name: 'server01' })
    expect(objectAriaLabel(_t, host, 'DOWN')).toBe('server01, Down')
    const service: MapElement = anObject({
      ...base,
      type: 'service',
      host_name: 'server01',
      service_description: 'CPU load'
    })
    expect(objectAriaLabel(_t, service, 'CRITICAL')).toBe('server01 / CPU load, Critical')
  })

  it('announces stateless objects explicitly', () => {
    const host: MapElement = anObject({ ...base, type: 'host', host_name: 'server01' })
    expect(objectAriaLabel(_t, host, undefined)).toBe('server01, No state')
  })

  it('uses the bare name for visual-only objects', () => {
    const textbox: MapElement = anObject({
      ...base,
      type: 'textbox',
      label: { show: true, text: 'Rack 3', x: 0, y: 0, size: 12, color: '', background: '' }
    })
    expect(objectAriaLabel(_t, textbox, undefined)).toBe('Rack 3')
  })
})

describe('stateAriaLabel', () => {
  it('covers every monitoring state with a readable word', () => {
    expect(stateAriaLabel(_t, 'NO_PERMISSION')).toBe('No permission')
    expect(stateAriaLabel(_t, 'UNREACHABLE')).toBe('Unreachable')
    expect(stateAriaLabel(_t, undefined)).toBe('No state')
  })
})
