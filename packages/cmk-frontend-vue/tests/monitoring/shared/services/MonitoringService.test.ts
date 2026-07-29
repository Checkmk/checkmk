/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, SortingState } from '@tanstack/vue-table'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { POLL_INTERVAL_MS } from '@/monitoring/shared/constants'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse,
  buildColumnStorageKey
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService, makeResponse } from './testHelpers'

interface TestItem {
  id: string
  value: number
}

class TestService extends MonitoringService<TestItem> {
  constructor(
    public readonly fetchBatchMock: (signal: AbortSignal) => Promise<PagedResponse<TestItem>>,
    options: MonitoringServiceOptions<TestItem> = {},
    shortCutService: KeyShortcutService = makeKeyShortcutService(),
    serviceId: string = 'test-service'
  ) {
    super(serviceId, shortCutService, options)
  }

  protected fetchBatch(signal: AbortSignal): Promise<PagedResponse<TestItem>> {
    return this.fetchBatchMock(signal)
  }
}

describe('MonitoringService', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with empty state before the first fetch fires', () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    expect(service.items.value).toEqual([])
    expect(service.matched.value).toBe(0)
    expect(service.total.value).toBe(0)
    expect(service.fetchState.value).toBe('idle')
    expect(fetchBatch).not.toHaveBeenCalled()

    service.stopPolling()
  })

  it('fetches once on construction and populates items/counts', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([{ id: 'a', value: 1 }], 42, 100))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])
    expect(service.matched.value).toBe(42)
    expect(service.total.value).toBe(100)
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('flips hasLoaded once the first fetch settles', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([{ id: 'a', value: 1 }], 1, 10))
    const service = new TestService(fetchBatch)

    expect(service.hasLoaded.value).toBe(false)
    await vi.advanceTimersByTimeAsync(0)
    expect(service.hasLoaded.value).toBe(true)

    service.stopPolling()
  })

  it('flips hasLoaded even when the first fetch rejects', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchBatch = vi.fn().mockRejectedValue(new Error('boom'))
    const service = new TestService(fetchBatch)

    expect(service.hasLoaded.value).toBe(false)
    await vi.advanceTimersByTimeAsync(0)
    expect(service.hasLoaded.value).toBe(true)

    service.stopPolling()
    consoleErrorSpy.mockRestore()
  })

  it('stays in a non-idle fetch state while a fetch is in flight', async () => {
    const pending = new Promise<PagedResponse<TestItem>>(() => {})
    const fetchBatch = vi.fn().mockReturnValue(pending)
    const service = new TestService(fetchBatch)

    expect(service.fetchState.value).toBe('idle')
    await vi.advanceTimersByTimeAsync(0)
    expect(service.fetchState.value).not.toBe('idle')
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.stopPolling()
  })

  it('polls at POLL_INTERVAL_MS and replaces items on each tick', async () => {
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([{ id: 'a', value: 1 }], 1, 10))
      .mockResolvedValueOnce(makeResponse([{ id: 'b', value: 2 }], 1, 10))
      .mockResolvedValueOnce(makeResponse([{ id: 'c', value: 3 }], 1, 10))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.items.value).toEqual([{ id: 'b', value: 2 }])

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(3)
    expect(service.items.value).toEqual([{ id: 'c', value: 3 }])

    service.stopPolling()
  })

  it('honors a custom poll interval passed to the constructor', async () => {
    const customInterval = 5_000
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, { pollIntervalMs: customInterval })

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(customInterval)
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('cancels the initial fetch when stopPolling() runs before it fires', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    service.stopPolling()
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2)

    expect(fetchBatch).not.toHaveBeenCalled()
    expect(service.fetchState.value).toBe('idle')
  })

  it('stops polling after stopPolling()', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.stopPolling()
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5)

    expect(fetchBatch).toHaveBeenCalledTimes(1)
  })

  it('skips a poll tick while a fetch is in flight', async () => {
    let resolveFirst: (value: PagedResponse<TestItem>) => void = () => {}
    const firstFetch = new Promise<PagedResponse<TestItem>>((resolve) => {
      resolveFirst = resolve
    })
    const fetchBatch = vi
      .fn()
      .mockReturnValueOnce(firstFetch)
      .mockResolvedValue(makeResponse([{ id: 'b', value: 2 }], 1, 10))

    const service = new TestService(fetchBatch)

    // Kick off the first fetch and leave it pending.
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.fetchState.value).not.toBe('idle')

    // Poll interval elapses — second call must be skipped because a fetch is in flight.
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    // Resolve the in-flight fetch; the fetch state returns to idle.
    resolveFirst(makeResponse([{ id: 'a', value: 1 }], 1, 10))
    await vi.advanceTimersByTimeAsync(0)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])
    expect(service.fetchState.value).toBe('idle')

    // Next poll tick fires normally.
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.items.value).toEqual([{ id: 'b', value: 2 }])

    service.stopPolling()
  })

  it('aborts an in-flight fetch when a new foreground fetch is triggered', async () => {
    const signals: AbortSignal[] = []
    const fetchBatch = vi
      .fn()
      .mockImplementationOnce((signal: AbortSignal) => {
        signals.push(signal)
        return new Promise<PagedResponse<TestItem>>(() => {})
      })
      .mockImplementationOnce((signal: AbortSignal) => {
        signals.push(signal)
        return makeResponse([{ id: 'b', value: 2 }], 1, 10)
      })
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(signals[0]!.aborted).toBe(false)

    service.updateSearch('db')
    await vi.advanceTimersByTimeAsync(0)

    expect(signals[0]!.aborted).toBe(true)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.items.value).toEqual([{ id: 'b', value: 2 }])
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('ignores the result of an aborted fetch and keeps the newer one', async () => {
    let resolveFirst: (value: PagedResponse<TestItem>) => void = () => {}
    const fetchBatch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<PagedResponse<TestItem>>((resolve) => {
            resolveFirst = resolve
          })
      )
      .mockImplementationOnce(() => makeResponse([{ id: 'new', value: 2 }], 1, 10))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    service.updateSearch('db')
    await vi.advanceTimersByTimeAsync(0)
    expect(service.items.value).toEqual([{ id: 'new', value: 2 }])

    resolveFirst(makeResponse([{ id: 'stale', value: 1 }], 9, 9))
    await vi.advanceTimersByTimeAsync(0)

    expect(service.items.value).toEqual([{ id: 'new', value: 2 }])
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('swallows an aborted fetch rejection without logging an error', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchBatch = vi
      .fn()
      .mockImplementationOnce(
        (signal: AbortSignal) =>
          new Promise<PagedResponse<TestItem>>((_resolve, reject) => {
            signal.addEventListener('abort', () => {
              reject(new DOMException('Aborted', 'AbortError'))
            })
          })
      )
      .mockImplementationOnce(() => makeResponse([{ id: 'b', value: 2 }], 1, 10))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    service.updateSearch('db')
    await vi.advanceTimersByTimeAsync(0)

    expect(service.items.value).toEqual([{ id: 'b', value: 2 }])
    expect(service.fetchState.value).toBe('idle')
    expect(consoleErrorSpy).not.toHaveBeenCalled()

    service.stopPolling()
    consoleErrorSpy.mockRestore()
  })

  it('returns to idle and logs when fetchBatch rejects', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchBatch = vi.fn().mockRejectedValue(new Error('boom'))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)

    expect(service.fetchState.value).toBe('idle')
    expect(service.items.value).toEqual([])
    expect(service.total.value).toBe(0)
    expect(service.matched.value).toBe(0)
    expect(consoleErrorSpy).toHaveBeenCalled()

    service.stopPolling()
    consoleErrorSpy.mockRestore()
  })

  it('updateSort triggers an immediate refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.updateSort([{ id: 'name', desc: false }] satisfies SortingState)
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('updateSearch stores the query and triggers an immediate refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.searchQuery.value).toBe('')

    service.updateSearch('db')
    await vi.advanceTimersByTimeAsync(0)

    expect(service.searchQuery.value).toBe('db')
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('refresh() triggers a silent background re-fetch', async () => {
    let resolveRefresh: (value: PagedResponse<TestItem>) => void = () => {}
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([], 0, 0))
      .mockReturnValueOnce(
        new Promise<PagedResponse<TestItem>>((resolve) => {
          resolveRefresh = resolve
        })
      )
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.refresh()
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.fetchState.value).toBe('background')

    resolveRefresh(makeResponse([{ id: 'a', value: 1 }], 1, 1))
    await vi.advanceTimersByTimeAsync(0)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('refresh(delayMs) defers the background re-fetch until the delay elapses', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.refresh(1000)
    await vi.advanceTimersByTimeAsync(999)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(1)
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('stopPolling() cancels a pending delayed refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.refresh(1000)
    service.stopPolling()
    await vi.advanceTimersByTimeAsync(1000)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
  })

  it('only updates committedSearchQuery once the triggered fetch resolves', async () => {
    let resolveFetch: (value: PagedResponse<TestItem>) => void = () => {}
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([], 0, 0))
      .mockImplementationOnce(
        () =>
          new Promise<PagedResponse<TestItem>>((resolve) => {
            resolveFetch = resolve
          })
      )
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(service.committedSearchQuery.value).toBe('')

    // Mirrors the live v-model binding: typing updates searchQuery before the fetch settles.
    service.updateSearch('db')
    expect(service.searchQuery.value).toBe('db')
    expect(service.committedSearchQuery.value).toBe('')

    resolveFetch(makeResponse([], 3, 10))
    await vi.advanceTimersByTimeAsync(0)

    expect(service.committedSearchQuery.value).toBe('db')

    service.stopPolling()
  })

  it('enters the foreground fetch state for a search/sort/filter fetch and returns to idle after', async () => {
    let resolveReload: (value: PagedResponse<TestItem>) => void = () => {}
    const reloadFetch = new Promise<PagedResponse<TestItem>>((resolve) => {
      resolveReload = resolve
    })
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([], 0, 0))
      .mockReturnValueOnce(reloadFetch)
    const service = new TestService(fetchBatch)

    // Initial fetch settles back to idle.
    await vi.advanceTimersByTimeAsync(0)
    expect(service.fetchState.value).toBe('idle')

    // A user-initiated search shows the skeleton via the foreground state.
    service.updateSearch('db')
    await vi.advanceTimersByTimeAsync(0)
    expect(service.fetchState.value).toBe('foreground')

    resolveReload(makeResponse([{ id: 'a', value: 1 }], 1, 1))
    await vi.advanceTimersByTimeAsync(0)
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('enters the background fetch state for a refresh-timer poll', async () => {
    let resolvePoll: (value: PagedResponse<TestItem>) => void = () => {}
    const pollFetch = new Promise<PagedResponse<TestItem>>((resolve) => {
      resolvePoll = resolve
    })
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([], 0, 0))
      .mockReturnValueOnce(pollFetch)
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    // Drive the refresh timer to trigger a poll; it must stay in the background state.
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.fetchState.value).toBe('background')

    resolvePoll(makeResponse([{ id: 'b', value: 2 }], 1, 1))
    await vi.advanceTimersByTimeAsync(0)
    expect(service.fetchState.value).toBe('idle')

    service.stopPolling()
  })

  it('dispatches the registered focus-search callback when the shortcut fires', () => {
    let shortcutCallback: (() => void) | undefined
    const shortCutService = {
      on: vi.fn((_shortcut: unknown, cb: () => void) => {
        shortcutCallback = cb
        return 'shortcut-id'
      }),
      remove: vi.fn()
    } as unknown as KeyShortcutService
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, undefined, shortCutService, 'focus-dispatch')

    const onFocus = vi.fn()
    service.onFocusSearch(onFocus)
    shortcutCallback?.()

    expect(onFocus).toHaveBeenCalledTimes(1)

    service.stopPolling()
  })

  it('activating a chip updates filterState and triggers a refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        {
          label: 'Down',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.filterState.value).toBeUndefined()

    const chip = service.filters.quickFilters[0]!
    service.filters.activateQuickFilter(chip)
    await vi.advanceTimersByTimeAsync(0)

    expect(service.filterState.value).toStrictEqual(chip.filter)
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.filters.deactivateQuickFilter(chip)
    await vi.advanceTimersByTimeAsync(0)

    expect(service.filterState.value).toBeUndefined()
    expect(fetchBatch).toHaveBeenCalledTimes(3)

    service.stopPolling()
  })

  it('a chip with an empty filter and search query shows all results', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        { label: 'All', searchQuery: '' },
        {
          label: 'Down',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)

    const allChip = service.filters.quickFilters[0]!
    const downChip = service.filters.quickFilters[1]!
    // No filters and no search query yet, so the "All" chip is active.
    expect(allChip.isActive.value).toBe(true)

    // Apply both a quick filter and a search query.
    service.activateQuickFilter(downChip)
    service.updateSearch('web')
    await vi.advanceTimersByTimeAsync(0)
    expect(service.filterState.value).toStrictEqual(downChip.filter)
    expect(service.searchQuery.value).toBe('web')
    expect(allChip.isActive.value).toBe(false)

    // Activating the "All" chip clears the filter and the search query, and refreshes.
    const callsBefore = fetchBatch.mock.calls.length
    service.activateQuickFilter(allChip)
    await vi.advanceTimersByTimeAsync(0)
    expect(service.filterState.value).toBeUndefined()
    expect(service.searchQuery.value).toBe('')
    expect(allChip.isActive.value).toBe(true)
    expect(fetchBatch.mock.calls.length).toBeGreaterThan(callsBefore)

    service.stopPolling()
  })

  it('a chip leaves the search query untouched when it declares no searchQuery', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        {
          label: 'Down',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)

    service.updateSearch('web')
    service.activateQuickFilter(service.filters.quickFilters[0]!)
    await vi.advanceTimersByTimeAsync(0)

    expect(service.searchQuery.value).toBe('web')

    service.stopPolling()
  })

  it('destruct() removes the focus-search callback so it is no longer dispatched', () => {
    let shortcutCallback: (() => void) | undefined
    const shortCutService = {
      on: vi.fn((_shortcut: unknown, cb: () => void) => {
        shortcutCallback = cb
        return 'shortcut-id'
      }),
      remove: vi.fn()
    } as unknown as KeyShortcutService
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, undefined, shortCutService, 'focus-destruct')

    const onFocus = vi.fn()
    service.onFocusSearch(onFocus)
    service.destruct()
    shortcutCallback?.()

    expect(onFocus).not.toHaveBeenCalled()
  })

  it('re-activates a chip when the filter is rebuilt to a structurally equal value', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        {
          label: 'Unacknowledged',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)
    const chip = service.filters.quickFilters[0]!

    service.filters.activateQuickFilter(chip)
    expect(chip.isActive.value).toBe(true)

    // Edit away from the preset via the column-filter path: a fresh node object.
    service.filters.setColumnFilters(
      new Map([
        ['acknowledged', { type: 'condition', field: 'acknowledged', op: 'eq', value: true }]
      ])
    )
    expect(chip.isActive.value).toBe(false)

    // Rebuild the same filter as the preset: a different object, but equal value.
    service.filters.setColumnFilters(
      new Map([
        ['acknowledged', { type: 'condition', field: 'acknowledged', op: 'eq', value: false }]
      ])
    )
    expect(service.filterState.value).not.toBe(chip.filter)
    expect(chip.isActive.value).toBe(true)

    service.stopPolling()
  })

  it('stops reacting to filter changes after stopPolling()', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        {
          label: 'Down',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)
    service.stopPolling()

    service.filters.activateQuickFilter(service.filters.quickFilters[0]!)
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(1)
  })

  describe('column visibility', () => {
    it('hides columns flagged meta.hidden by default and leaves the rest visible', () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch, {
        columns: [
          { id: 'select', header: '', meta: { selectColumn: true } },
          { accessorKey: 'value', header: 'Value' },
          { accessorKey: 'alias', header: 'Alias', meta: { hidden: true } }
        ]
      })

      // Only flagged columns are present in the map; others default to visible.
      expect(service.columnVisibility.value).toEqual({ alias: false })

      service.stopPolling()
    })

    it('offers toggleable columns in order, excluding select and enableHiding:false', () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch, {
        columns: [
          { id: 'select', header: '', meta: { selectColumn: true } },
          { accessorKey: 'name', header: 'Host', enableHiding: false },
          { accessorKey: 'address', header: 'IP address' },
          { accessorKey: 'alias', header: 'Alias', meta: { hidden: true } }
        ]
      })

      expect(service.toggleableColumns).toEqual([
        { id: 'address', label: 'IP address' },
        { id: 'alias', label: 'Alias' }
      ])

      service.stopPolling()
    })

    it('refetches when a column is revealed, whose data may never have been fetched', async () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch, {
        columns: [{ accessorKey: 'alias', header: 'Alias', meta: { hidden: true } }]
      })

      await vi.advanceTimersByTimeAsync(0)
      expect(fetchBatch).toHaveBeenCalledTimes(1)

      service.updateColumnVisibility({ alias: true })
      await vi.advanceTimersByTimeAsync(0)

      expect(service.columnVisibility.value).toEqual({ alias: true })
      expect(fetchBatch).toHaveBeenCalledTimes(2)

      service.stopPolling()
    })

    it('does not refetch when a column is hidden, its data being here already', async () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch, {
        columns: [{ accessorKey: 'address', header: 'IP address' }]
      })

      await vi.advanceTimersByTimeAsync(0)
      expect(fetchBatch).toHaveBeenCalledTimes(1)

      service.updateColumnVisibility({ address: false })
      await vi.advanceTimersByTimeAsync(0)

      expect(service.columnVisibility.value).toEqual({ address: false })
      expect(fetchBatch).toHaveBeenCalledTimes(1)

      service.stopPolling()
    })

    describe('persistence', () => {
      const STORAGE_KEY = 'test-service-columns'
      const COLUMNS: ColumnDef<TestItem>[] = [
        { id: 'select', header: '', meta: { selectColumn: true } },
        { accessorKey: 'name', header: 'Host', enableHiding: false },
        { accessorKey: 'address', header: 'IP address' },
        { accessorKey: 'alias', header: 'Alias', meta: { hidden: true } }
      ]

      function makePersistingService(columnStorageKey: string = STORAGE_KEY): TestService {
        const service = new TestService(vi.fn().mockResolvedValue(makeResponse([], 0, 0)), {
          columns: COLUMNS,
          columnStorageKey
        })
        service.stopPolling()
        return service
      }

      function stored(): unknown {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
      }

      afterEach(() => {
        localStorage.clear()
      })

      it('starts from the default set when storage is empty', () => {
        expect(makePersistingService().columnVisibility.value).toEqual({ alias: false })
      })

      it('keys a selection by view, site, user and edition', () => {
        expect(
          buildColumnStorageKey({
            view: 'all-hosts',
            site: 'heute',
            userId: 'harri',
            edition: 'community'
          })
        ).toBe('monitoring-all-hosts-columns-heute-harri-community')
      })

      it('keeps the same user on another site out of the stored selection', () => {
        // Browser storage is shared by every site served from one host, where a
        // user id can mean two unrelated accounts.
        const scope = { view: 'all-hosts', site: 'heute', userId: 'harri', edition: 'community' }
        localStorage.setItem(buildColumnStorageKey(scope), JSON.stringify({ alias: true }))

        const other = makePersistingService(buildColumnStorageKey({ ...scope, site: 'heute_2' }))
          .columnVisibility.value

        expect(other).toEqual({ alias: false })
      })

      it('restores a stored selection over the defaults', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ alias: true, address: false }))

        expect(makePersistingService().columnVisibility.value).toEqual({
          alias: true,
          address: false
        })
      })

      it('writes a changed selection to storage', async () => {
        const service = makePersistingService()

        service.updateColumnVisibility({ alias: true })
        await nextTick()

        expect(stored()).toEqual({ alias: true })
      })

      it('writes the default set back when the selection is reset', async () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ alias: true }))
        const service = makePersistingService()

        service.resetColumnVisibility()
        await nextTick()

        expect(stored()).toEqual({ alias: false })
      })

      it('ignores stored entries for columns that are no longer offered', () => {
        // 'gone' was dropped from the table and 'name' has become fixed since
        // this selection was stored; neither may still hide anything.
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ gone: false, name: false, alias: true }))

        expect(makePersistingService().columnVisibility.value).toEqual({ alias: true })
      })

      it('falls back to the defaults when storage holds something unusable', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(['alias']))

        expect(makePersistingService().columnVisibility.value).toEqual({ alias: false })
      })

      it('keeps the selection in memory when no storage key is given', async () => {
        const service = new TestService(vi.fn().mockResolvedValue(makeResponse([], 0, 0)), {
          columns: COLUMNS
        })
        service.stopPolling()

        service.updateColumnVisibility({ alias: true })
        await nextTick()

        expect(localStorage.length).toBe(0)
      })
    })

    it('resetColumnVisibility restores the default column set', () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch, {
        columns: [
          { accessorKey: 'address', header: 'IP address' },
          { accessorKey: 'alias', header: 'Alias', meta: { hidden: true } }
        ]
      })

      service.updateColumnVisibility({ alias: true, address: false })
      expect(service.columnVisibility.value).toEqual({ alias: true, address: false })

      service.resetColumnVisibility()
      expect(service.columnVisibility.value).toEqual({ alias: false })

      service.stopPolling()
    })
  })

  describe('paging', () => {
    function makePagedService(matched: number, pageSize: number, maxOffset?: number) {
      const items = Array.from({ length: pageSize }, (_unused, index) => ({
        id: `item-${index}`,
        value: index
      }))
      // Echo back whichever offset was asked for, the way a paging backend does.
      // The holder breaks the cycle: the mock is needed to build the service.
      const paged: { service?: TestService } = {}
      const fetchBatch = vi.fn().mockImplementation(() =>
        Promise.resolve({
          items,
          meta: {
            limit: pageSize,
            matched,
            total: matched,
            offset: paged.service?.offset.value ?? 0,
            ...(maxOffset === undefined ? {} : { maxOffset })
          }
        })
      )
      const service = new TestService(fetchBatch, { limitTiers: [pageSize] })
      paged.service = service
      return { fetchBatch, service }
    }

    it('starts unpaged, with no offset and no ceiling', async () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch)

      await vi.advanceTimersByTimeAsync(0)

      expect(service.offset.value).toBe(0)
      // A listing whose backend does not page never reports one.
      expect(service.maxOffset.value).toBeNull()
      expect(service.hasPreviousPage.value).toBe(false)

      service.stopPolling()
    })

    it('reports the page bounds of the visible rows', async () => {
      const { service } = makePagedService(1000, 100)
      await vi.advanceTimersByTimeAsync(0)

      expect(service.pageFirst.value).toBe(1)
      expect(service.pageLast.value).toBe(100)

      service.stopPolling()
    })

    it('reports zero bounds while nothing matched', async () => {
      const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0, 0))
      const service = new TestService(fetchBatch)
      await vi.advanceTimersByTimeAsync(0)

      expect(service.pageFirst.value).toBe(0)
      expect(service.pageLast.value).toBe(0)

      service.stopPolling()
    })

    it('nextPage steps by the page size and refetches', async () => {
      const { fetchBatch, service } = makePagedService(1000, 100)
      await vi.advanceTimersByTimeAsync(0)

      service.nextPage()
      await vi.advanceTimersByTimeAsync(0)

      expect(service.offset.value).toBe(100)
      expect(fetchBatch).toHaveBeenCalledTimes(2)

      service.stopPolling()
    })

    it('previousPage steps back and never below zero', async () => {
      const { service } = makePagedService(1000, 100)
      await vi.advanceTimersByTimeAsync(0)

      service.setOffset(50)
      await vi.advanceTimersByTimeAsync(0)
      service.previousPage()
      await vi.advanceTimersByTimeAsync(0)

      expect(service.offset.value).toBe(0)

      service.stopPolling()
    })

    it('has no next page once the matched rows run out', async () => {
      const { service } = makePagedService(100, 100)
      await vi.advanceTimersByTimeAsync(0)

      expect(service.hasNextPage.value).toBe(false)

      service.stopPolling()
    })

    it('stops at the offset ceiling the backend reports', async () => {
      const { service } = makePagedService(1_000_000, 100, 150)
      await vi.advanceTimersByTimeAsync(0)

      // 100 is still within the ceiling, 200 would exceed it.
      expect(service.hasNextPage.value).toBe(true)
      service.setOffset(100)
      await vi.advanceTimersByTimeAsync(0)
      expect(service.hasNextPage.value).toBe(false)

      service.stopPolling()
    })

    it.each([
      ['updateSearch', (service: TestService) => service.updateSearch('web')],
      ['updateSort', (service: TestService) => service.updateSort([{ id: 'name', desc: false }])],
      [
        'updateFilters',
        (service: TestService) =>
          service.updateFilters({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
      ],
      ['setRequestedLimit', (service: TestService) => service.setRequestedLimit(1000)]
    ])('%s resets the offset, because it invalidates the page', async (_name, narrow) => {
      const { service } = makePagedService(1000, 100)
      await vi.advanceTimersByTimeAsync(0)
      service.setOffset(300)
      await vi.advanceTimersByTimeAsync(0)
      expect(service.offset.value).toBe(300)

      narrow(service)

      expect(service.offset.value).toBe(0)

      service.stopPolling()
    })

    it('trusts the offset the backend served over the requested one', async () => {
      const fetchBatch = vi.fn().mockResolvedValue({
        items: [{ id: 'a', value: 1 }],
        meta: { limit: 100, matched: 500, total: 500, offset: 42 }
      })
      const service = new TestService(fetchBatch, { limitTiers: [100] })

      await vi.advanceTimersByTimeAsync(0)

      expect(service.offset.value).toBe(42)

      service.stopPolling()
    })
  })
})
