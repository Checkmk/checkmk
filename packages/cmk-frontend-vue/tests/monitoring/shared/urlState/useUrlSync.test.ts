/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { type Ref, computed, nextTick, ref } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import type { UrlStateWriter } from '@/monitoring/shared/urlState/types'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'

/** Remembers what was written, so a later flush sees the URL its predecessor left behind. */
function makeUrlSync(search = ''): { urlSync: UrlSync; replaceUrl: ReturnType<typeof vi.fn> } {
  let current = search
  const replaceUrl = vi.fn((url: string) => {
    const query = url.indexOf('?')
    current = query === -1 ? '' : url.slice(query)
  })
  return {
    urlSync: {
      getCurrentUrl: () => ({ pathname: '/monitor_all_hosts.py', search: current, hash: '' }),
      replaceUrl
    },
    replaceUrl
  }
}

function makeWriter(
  name: string,
  keys: string[],
  params: Ref<Record<string, string | null>>
): UrlStateWriter {
  return { name, keys, params: computed(() => params.value) }
}

describe('useUrlSync', () => {
  it('collects every slice into a single write', async () => {
    const first = ref<Record<string, string | null>>({ cols: null })
    const second = ref<Record<string, string | null>>({ q: null })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([makeWriter('first', ['cols'], first), makeWriter('second', ['q'], second)], {
      urlSync
    })

    first.value = { cols: 'address' }
    second.value = { q: 'web01' }
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(1)
    expect(replaceUrl.mock.calls[0]![0]).toBe('/monitor_all_hosts.py?cols=address&q=web01')
  })

  it('rejects a slice claiming a param another slice already owns', () => {
    const params = ref<Record<string, string | null>>({})

    expect(() =>
      useUrlSync(
        [
          makeWriter('table state', ['cols', 'q'], params),
          makeWriter('filter state', ['q'], params)
        ],
        { urlSync: makeUrlSync().urlSync }
      )
    ).toThrow(/'filter state' claims the URL param 'q', which 'table state' already owns/)
  })

  it('ignores a write to a param another slice owns, keeping the owner value', async () => {
    const owner = ref<Record<string, string | null>>({ q: 'owned' })
    const intruder = ref<Record<string, string | null>>({})
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([makeWriter('owner', ['q'], owner), makeWriter('intruder', [], intruder)], {
      urlSync
    })

    intruder.value = { q: 'stomped' }
    await nextTick()

    expect(consoleError).toHaveBeenCalledWith(expect.stringContaining("'q', which 'owner' owns"))
    for (const call of replaceUrl.mock.calls) {
      expect(call[0] as string).toContain('q=owned')
    }

    consoleError.mockRestore()
  })

  it('drops a param a slice wrote before but no longer writes', async () => {
    const params = ref<Record<string, string | null>>({ host_regex: 'web' })
    const { urlSync, replaceUrl } = makeUrlSync()

    useUrlSync([makeWriter('flow filters', ['_active'], params)], { urlSync })
    expect(replaceUrl.mock.calls[0]![0]).toContain('host_regex=web')

    params.value = {}
    await nextTick()

    expect(replaceUrl).toHaveBeenCalledTimes(2)
    expect(replaceUrl.mock.calls[1]![0]).toBe('/monitor_all_hosts.py')
  })

  it('leaves the URL alone when it already says what the slices do', () => {
    const params = ref<Record<string, string | null>>({ q: 'web01' })
    const { urlSync, replaceUrl } = makeUrlSync('?q=web01')

    useUrlSync([makeWriter('filter state', ['q'], params)], { urlSync })

    expect(replaceUrl).not.toHaveBeenCalled()
  })
})
