/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SidebarSnapin } from 'cmk-shared-typing/typescript/sidebar'
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, beforeEach, expect, vi } from 'vitest'

import { SidebarService } from '@/sidebar/lib/sidebar'

const getSidebarSnapinContentsMock = vi.hoisted(() => vi.fn())

vi.mock('@/sidebar/lib/sidebar-api-client', () => ({
  SidebarApiClient: class {
    public getSidebarSnapinContents = getSidebarSnapinContentsMock
  }
}))

function makeSnapin(name: string): SidebarSnapin {
  return { name, title: name, refresh_regularly: true }
}

function renderSnapin(name: string, withInput = false): void {
  const container = document.createElement('div')
  container.id = `snapin_${name}`
  if (withInput) {
    const input = document.createElement('input')
    input.id = `input_${name}`
    container.appendChild(input)
  }
  document.body.appendChild(container)
}

function focusSnapinInput(name: string): void {
  document.getElementById(`input_${name}`)!.focus()
}

const shortCutServiceStub = {
  on: vi.fn(() => 'shortcut-id'),
  remove: vi.fn()
} as unknown as KeyShortcutService

// The service queries `:focus-within` during construction (init -> updateSnapinContent).
// jsdom's selector engine caches that result per element and does not invalidate it on a
// later focus change, so the DOM must already reflect the intended focus state before the
// service is constructed - which also mirrors reality: the user focuses a field, then a
// periodic reload fires.
function createService(names: string[]): SidebarService {
  const service = new SidebarService(names.map(makeSnapin), 30, shortCutServiceStub)
  getSidebarSnapinContentsMock.mockClear()
  return service
}

beforeEach(() => {
  vi.useFakeTimers()
  getSidebarSnapinContentsMock.mockResolvedValue({})
})

afterEach(() => {
  vi.runOnlyPendingTimers()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('SidebarService.snapinHasFocus', () => {
  test('returns false when the snapin element does not exist', () => {
    const service = createService(['quicksearch'])
    expect(service.snapinHasFocus('quicksearch')).toBe(false)
  })

  test('returns false when the snapin exists but nothing inside is focused', () => {
    renderSnapin('quicksearch', true)
    const service = createService(['quicksearch'])
    expect(service.snapinHasFocus('quicksearch')).toBe(false)
  })

  test('returns true when a descendant of the snapin has focus', () => {
    renderSnapin('quicksearch', true)
    focusSnapinInput('quicksearch')
    const service = createService(['quicksearch'])
    expect(service.snapinHasFocus('quicksearch')).toBe(true)
  })
})

describe('SidebarService.updateSnapinContent', () => {
  test('skips fetching content for a snapin that currently has focus', async () => {
    renderSnapin('quicksearch', true)
    renderSnapin('hosts')
    focusSnapinInput('quicksearch')
    const service = createService(['quicksearch', 'hosts'])

    await service.updateSnapinContent(['quicksearch', 'hosts'])

    expect(getSidebarSnapinContentsMock).toHaveBeenCalledTimes(1)
    expect(getSidebarSnapinContentsMock).toHaveBeenCalledWith(['hosts'], expect.any(Number))
  })

  test('does not fetch or dispatch when every requested snapin has focus', async () => {
    renderSnapin('quicksearch', true)
    focusSnapinInput('quicksearch')
    const service = createService(['quicksearch'])

    const onUpdate = vi.fn()
    service.onUpdateSnapinContent(onUpdate)

    await service.updateSnapinContent(['quicksearch'])

    expect(getSidebarSnapinContentsMock).not.toHaveBeenCalled()
    expect(onUpdate).not.toHaveBeenCalled()
  })

  test('fetches content for all snapins when none has focus', async () => {
    renderSnapin('quicksearch', true)
    renderSnapin('hosts')
    const service = createService(['quicksearch', 'hosts'])

    await service.updateSnapinContent(['quicksearch', 'hosts'])

    expect(getSidebarSnapinContentsMock).toHaveBeenCalledWith(
      ['quicksearch', 'hosts'],
      expect.any(Number)
    )
  })
})
