/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { KeyShortcutService } from '@/lib/keyShortcuts'

import { POLL_INTERVAL_MS } from '@/monitoring/shared/constants'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import { makeKeyShortcutService, makeResponse } from './testHelpers'

interface TestItem {
  id: string
  value: number
}

class TestService extends MonitoringService<TestItem> {
  constructor(
    public readonly fetchBatchMock: () => Promise<PagedResponse<TestItem>>,
    options: MonitoringServiceOptions<TestItem> = {},
    shortCutService: KeyShortcutService = makeKeyShortcutService(),
    serviceId: string = 'test-service'
  ) {
    super(serviceId, shortCutService, options)
  }

  protected fetchBatch(): Promise<PagedResponse<TestItem>> {
    return this.fetchBatchMock()
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
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch)

    expect(service.items.value).toEqual([])
    expect(service.total.value).toBe(0)
    expect(service.loading.value).toBe(false)
    expect(fetchBatch).not.toHaveBeenCalled()

    service.stopPolling()
  })

  it('fetches once on construction and populates items/total', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([{ id: 'a', value: 1 }], 42))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])
    expect(service.total.value).toBe(42)
    expect(service.loading.value).toBe(false)

    service.stopPolling()
  })

  it('flips hasLoaded once the first fetch settles', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([{ id: 'a', value: 1 }], 1))
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

  it('keeps loading=true while a fetch is in flight', async () => {
    const pending = new Promise<PagedResponse<TestItem>>(() => {})
    const fetchBatch = vi.fn().mockReturnValue(pending)
    const service = new TestService(fetchBatch)

    expect(service.loading.value).toBe(false)
    await vi.advanceTimersByTimeAsync(0)
    expect(service.loading.value).toBe(true)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.stopPolling()
  })

  it('polls at POLL_INTERVAL_MS and replaces items on each tick', async () => {
    const fetchBatch = vi
      .fn()
      .mockResolvedValueOnce(makeResponse([{ id: 'a', value: 1 }], 1))
      .mockResolvedValueOnce(makeResponse([{ id: 'b', value: 2 }], 1))
      .mockResolvedValueOnce(makeResponse([{ id: 'c', value: 3 }], 1))
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
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch, { pollIntervalMs: customInterval })

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(customInterval)
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('cancels the initial fetch when stopPolling() runs before it fires', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch)

    service.stopPolling()
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2)

    expect(fetchBatch).not.toHaveBeenCalled()
    expect(service.loading.value).toBe(false)
  })

  it('stops polling after stopPolling()', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
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
      .mockResolvedValue(makeResponse([{ id: 'b', value: 2 }], 1))

    const service = new TestService(fetchBatch)

    // Kick off the first fetch and leave it pending.
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)
    expect(service.loading.value).toBe(true)

    // Poll interval elapses — second call must be skipped because loading=true.
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    // Resolve the in-flight fetch; loading clears.
    resolveFirst(makeResponse([{ id: 'a', value: 1 }], 1))
    await vi.advanceTimersByTimeAsync(0)
    expect(service.items.value).toEqual([{ id: 'a', value: 1 }])
    expect(service.loading.value).toBe(false)

    // Next poll tick fires normally.
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    expect(fetchBatch).toHaveBeenCalledTimes(2)
    expect(service.items.value).toEqual([{ id: 'b', value: 2 }])

    service.stopPolling()
  })

  it('clears loading and logs when fetchBatch rejects', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchBatch = vi.fn().mockRejectedValue(new Error('boom'))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)

    expect(service.loading.value).toBe(false)
    expect(service.items.value).toEqual([])
    expect(service.total.value).toBe(0)
    expect(consoleErrorSpy).toHaveBeenCalled()

    service.stopPolling()
    consoleErrorSpy.mockRestore()
  })

  it('updateSort triggers an immediate refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch)

    await vi.advanceTimersByTimeAsync(0)
    expect(fetchBatch).toHaveBeenCalledTimes(1)

    service.updateSort([{ id: 'name', desc: false }] satisfies SortingState)
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.stopPolling()
  })

  it('updateSearch stores the query and triggers an immediate refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
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

  it('dispatches the registered focus-search callback when the shortcut fires', () => {
    let shortcutCallback: (() => void) | undefined
    const shortCutService = {
      on: vi.fn((_shortcut: unknown, cb: () => void) => {
        shortcutCallback = cb
        return 'shortcut-id'
      }),
      remove: vi.fn()
    } as unknown as KeyShortcutService
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch, undefined, shortCutService, 'focus-dispatch')

    const onFocus = vi.fn()
    service.onFocusSearch(onFocus)
    shortcutCallback?.()

    expect(onFocus).toHaveBeenCalledTimes(1)

    service.stopPolling()
  })

  it('activating a chip updates filterState and triggers a refresh', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
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

    const chip = service.filters.chips[0]!
    service.filters.activateChip(chip)
    await vi.advanceTimersByTimeAsync(0)

    expect(service.filterState.value).toStrictEqual(chip.filter)
    expect(fetchBatch).toHaveBeenCalledTimes(2)

    service.filters.deactivateChip(chip)
    await vi.advanceTimersByTimeAsync(0)

    expect(service.filterState.value).toBeUndefined()
    expect(fetchBatch).toHaveBeenCalledTimes(3)

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
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch, undefined, shortCutService, 'focus-destruct')

    const onFocus = vi.fn()
    service.onFocusSearch(onFocus)
    service.destruct()
    shortcutCallback?.()

    expect(onFocus).not.toHaveBeenCalled()
  })

  it('re-activates a chip when the filter is rebuilt to a structurally equal value', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
    const service = new TestService(fetchBatch, {
      quickFilters: [
        {
          label: 'Unacknowledged',
          filter: { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        }
      ]
    })

    await vi.advanceTimersByTimeAsync(0)
    const chip = service.filters.chips[0]!

    service.filters.activateChip(chip)
    expect(chip.isActive.value).toBe(true)

    // Edit away from the preset via the column-filter path: a fresh node object.
    service.filters.setColumnConditions(
      new Map([
        ['acknowledged', { type: 'condition', field: 'acknowledged', op: 'eq', value: true }]
      ])
    )
    expect(chip.isActive.value).toBe(false)

    // Rebuild the same filter as the preset: a different object, but equal value.
    service.filters.setColumnConditions(
      new Map([
        ['acknowledged', { type: 'condition', field: 'acknowledged', op: 'eq', value: false }]
      ])
    )
    expect(service.filterState.value).not.toBe(chip.filter)
    expect(chip.isActive.value).toBe(true)

    service.stopPolling()
  })

  it('stops reacting to filter changes after stopPolling()', async () => {
    const fetchBatch = vi.fn().mockResolvedValue(makeResponse([], 0))
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

    service.filters.activateChip(service.filters.chips[0]!)
    await vi.advanceTimersByTimeAsync(0)

    expect(fetchBatch).toHaveBeenCalledTimes(1)
  })
})
