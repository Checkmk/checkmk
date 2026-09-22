/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import {
  displayOptionsFormat,
  displayOptionsWriter,
  readDisplayOptionsFromUrl,
  seedDisplayOptions
} from '@/monitoring/shared/displayOptionsState/urlState'
import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from '@/monitoring/shared/types'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'

/** Stateful, unlike a fixed-search stub: a later assertion may depend on an earlier write. */
function makeUrlSync(search = ''): { urlSync: UrlSync; replaceUrl: ReturnType<typeof vi.fn> } {
  let current = search
  const replaceUrl = vi.fn((url: string) => {
    current = url.includes('?') ? url.slice(url.indexOf('?')) : ''
  })
  return {
    urlSync: {
      getCurrentUrl: () => ({ pathname: '/monitor_all_hosts.py', search: current, hash: '' }),
      replaceUrl,
      pushUrl: replaceUrl,
      onNavigate: () => () => {}
    },
    replaceUrl
  }
}

describe('readDisplayOptionsFromUrl', () => {
  it('decodes both fields when the URL names them', () => {
    const state = readDisplayOptionsFromUrl('?date_format=%d.%m.%Y&timestamp_format=epoch')
    expect(state).toEqual({ dateFormat: '%d.%m.%Y', timestampFormat: 'epoch' })
  })

  it('leaves an unnamed field undefined - "no opinion", not "default"', () => {
    expect(readDisplayOptionsFromUrl('?date_format=%d.%m.%Y').timestampFormat).toBeUndefined()
    expect(readDisplayOptionsFromUrl('')).toEqual({
      dateFormat: undefined,
      timestampFormat: undefined
    })
  })

  it('drops a value that is not one of the offered choices', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const state = readDisplayOptionsFromUrl('?timestamp_format=bogus')

    expect(state.timestampFormat).toBeUndefined()
    warn.mockRestore()
  })
})

describe('displayOptionsFormat.codec.encode', () => {
  const encode = displayOptionsFormat.codec.encode

  it('omits both keys at the default', () => {
    expect(encode(DEFAULT_DISPLAY_OPTIONS)).toEqual({
      date_format: null,
      timestamp_format: null
    })
  })

  it('spells out a field that differs from the default', () => {
    const state: DisplayOptions = { dateFormat: '%d.%m.%Y', timestampFormat: 'epoch' }
    expect(encode(state)).toEqual({ date_format: '%d.%m.%Y', timestamp_format: 'epoch' })
  })

  it('treats "no opinion" the same as "at the default"', () => {
    expect(encode({ dateFormat: undefined, timestampFormat: undefined })).toEqual({
      date_format: null,
      timestamp_format: null
    })
  })
})

describe('seedDisplayOptions', () => {
  const stored: DisplayOptions = { dateFormat: '%m/%d/%Y', timestampFormat: 'abs' }

  it('prefers the URL field when it has an opinion', () => {
    expect(
      seedDisplayOptions({ dateFormat: '%d.%m.%Y', timestampFormat: undefined }, stored)
    ).toEqual({ dateFormat: '%d.%m.%Y', timestampFormat: 'abs' })
  })

  it('falls back to storage per field when the URL says nothing', () => {
    expect(
      seedDisplayOptions({ dateFormat: undefined, timestampFormat: undefined }, stored)
    ).toEqual(stored)
  })
})

describe('displayOptionsWriter', () => {
  it('writes nothing for a ref already at its default', () => {
    const displayOptions = ref<DisplayOptions>({ ...DEFAULT_DISPLAY_OPTIONS })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([displayOptionsWriter(displayOptions)], { urlSync })

    expect(replaceUrl).not.toHaveBeenCalled()
  })

  it('mirrors a later change into the URL', async () => {
    const displayOptions = ref<DisplayOptions>({ ...DEFAULT_DISPLAY_OPTIONS })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([displayOptionsWriter(displayOptions)], { urlSync })
    displayOptions.value = { dateFormat: '%d.%m.', timestampFormat: 'rel' }
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(1)
    const url = replaceUrl.mock.calls[0]![0] as string
    const params = new URLSearchParams(url.split('?')[1])
    expect(params.get('date_format')).toBe('%d.%m.')
    expect(params.get('timestamp_format')).toBe('rel')
  })

  it('drops a field back out of the URL once it returns to its default', async () => {
    const displayOptions = ref<DisplayOptions>({ ...DEFAULT_DISPLAY_OPTIONS })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([displayOptionsWriter(displayOptions)], { urlSync })
    displayOptions.value = { dateFormat: '%d.%m.', timestampFormat: 'rel' }
    await nextTick()
    displayOptions.value = { ...DEFAULT_DISPLAY_OPTIONS }
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(2)
    const url = replaceUrl.mock.calls[1]![0] as string
    expect(url).not.toContain('date_format=')
    expect(url).not.toContain('timestamp_format=')
  })
})
