/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { type Ref, computed, effectScope, nextTick, ref } from 'vue'

import type { UrlSync } from '@/monitoring/shared/browserUrlSync'
import type { UrlStateWriter } from '@/monitoring/shared/urlState/types'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'

const PATHNAME = '/monitor_all_hosts.py'

interface FakeUrl {
  urlSync: UrlSync
  replaceUrl: ReturnType<typeof vi.fn>
  pushUrl: ReturnType<typeof vi.fn>
  /** Puts the browser on `url` and fires the navigation, as Back and Forward do. */
  navigateTo: (url: string) => void
  written: () => string[]
}

/**
 * Remembers what was written, so a later flush sees the URL its predecessor
 * left behind - the skip-when-unchanged and drop-what-I-wrote rules are only
 * meaningful against a URL that actually moves.
 */
function makeUrlSync(url = PATHNAME): FakeUrl {
  let current = url
  const listeners: Array<() => void> = []
  const written: string[] = []
  const write = (next: string): void => {
    current = next
    written.push(next)
  }
  const replaceUrl = vi.fn(write)
  const pushUrl = vi.fn(write)
  return {
    urlSync: {
      getCurrentUrl: () => {
        const [beforeHash, hash = ''] = current.split('#')
        const [pathname = '', search = ''] = beforeHash!.split('?')
        return {
          pathname,
          search: search === '' ? '' : `?${search}`,
          hash: hash === '' ? '' : `#${hash}`
        }
      },
      replaceUrl,
      pushUrl,
      onNavigate: (listener) => {
        listeners.push(listener)
        return () => listeners.splice(listeners.indexOf(listener), 1)
      }
    },
    replaceUrl,
    pushUrl,
    navigateTo: (next) => {
      current = next
      for (const listener of [...listeners]) {
        listener()
      }
    },
    written: () => written
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
    const { urlSync, replaceUrl } = makeUrlSync(`${PATHNAME}?q=web01`)

    useUrlSync([makeWriter('filter state', ['q'], params)], { urlSync })

    expect(replaceUrl).not.toHaveBeenCalled()
  })

  it('writes a hash slice into the fragment, leaving the query to the query slices', async () => {
    const query = ref<Record<string, string | null>>({ q: 'web01' })
    const fragment = ref<Record<string, string | null>>({ host: null })
    const { urlSync, written } = makeUrlSync()

    useUrlSync(
      [
        makeWriter('filter state', ['q'], query),
        { ...makeWriter('slide-in', ['host'], fragment), target: 'hash' }
      ],
      { urlSync }
    )

    fragment.value = { host: 'web01' }
    await nextTick()

    expect(written().at(-1)).toBe(`${PATHNAME}?q=web01#host=web01`)
  })

  it('gives a push slice its own history entry, and keeps replacing for the others', async () => {
    const query = ref<Record<string, string | null>>({ q: null })
    const fragment = ref<Record<string, string | null>>({ host: null })
    const { urlSync, replaceUrl, pushUrl } = makeUrlSync()

    useUrlSync(
      [
        makeWriter('filter state', ['q'], query),
        { ...makeWriter('slide-in', ['host'], fragment), target: 'hash', history: 'push' }
      ],
      { urlSync }
    )

    query.value = { q: 'web' }
    await nextTick()
    expect(replaceUrl).toHaveBeenCalledTimes(1)
    expect(pushUrl).not.toHaveBeenCalled()

    fragment.value = { host: 'web01' }
    await nextTick()
    expect(pushUrl).toHaveBeenCalledTimes(1)
    expect(pushUrl.mock.calls[0]![0]).toBe(`${PATHNAME}?q=web#host=web01`)
  })

  it('hands a slice what the URL says once the user walks the history', () => {
    const applied: Array<Record<string, string>> = []
    const fragment = ref<Record<string, string | null>>({ host: 'web01' })
    const { urlSync, navigateTo } = makeUrlSync(`${PATHNAME}#host=web01`)
    const scope = effectScope()

    scope.run(() => {
      useUrlSync(
        [
          {
            ...makeWriter('slide-in', ['host'], fragment),
            target: 'hash',
            history: 'push',
            apply: (params) => applied.push(params)
          }
        ],
        { urlSync }
      )
    })

    navigateTo(PATHNAME)

    expect(applied).toEqual([{}])

    scope.stop()
  })

  it('applies one navigation once, however many events the browser fires for it', () => {
    const applied: Array<Record<string, string>> = []
    const fragment = ref<Record<string, string | null>>({ host: 'web01' })
    const { urlSync, navigateTo } = makeUrlSync(`${PATHNAME}#host=web01`)
    const scope = effectScope()

    scope.run(() => {
      useUrlSync(
        [
          {
            ...makeWriter('slide-in', ['host'], fragment),
            target: 'hash',
            history: 'push',
            apply: (params) => applied.push(params)
          }
        ],
        { urlSync }
      )
    })

    navigateTo(PATHNAME)
    navigateTo(PATHNAME)

    expect(applied).toEqual([{}])

    scope.stop()
  })

  it('stops listening for navigation once its scope is gone', () => {
    const applied: Array<Record<string, string>> = []
    const fragment = ref<Record<string, string | null>>({})
    const { urlSync, navigateTo } = makeUrlSync()
    const scope = effectScope()

    scope.run(() => {
      useUrlSync(
        [
          {
            ...makeWriter('slide-in', ['host'], fragment),
            target: 'hash',
            apply: (params) => applied.push(params)
          }
        ],
        { urlSync }
      )
    })
    scope.stop()

    navigateTo(`${PATHNAME}#host=web01`)

    expect(applied).toEqual([])
  })
})
