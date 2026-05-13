/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'

import { useDismissDialog } from '@/lib/useDismissDialog'

const DISMISS_ENDPOINT = 'api/1.0/domain-types/user_config/actions/dismiss-warning/invoke'

const mockCookie = vi.fn()
let fetchMock: ReturnType<typeof vi.fn>

beforeAll(() => {
  Object.defineProperty(document, 'cookie', { get: mockCookie, configurable: true })
})

beforeEach(() => {
  sessionStorage.clear()
  mockCookie.mockReturnValue('')
  fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function cookieWithDismissed(...warnings: string[]): string {
  const value = encodeURIComponent(JSON.stringify({ dismissed_warnings: warnings }))
  return `user_frontend_config=${value}`
}

function renderDismissDialog(key: string | undefined) {
  let api!: ReturnType<typeof useDismissDialog>
  const component = defineComponent({
    setup() {
      api = useDismissDialog(key)
      return () => null
    }
  })
  render(component)
  return api
}

test('shows the dialog by default when the warning has not been dismissed', () => {
  const { isShown } = renderDismissDialog('changes-info')

  expect(isShown.value).toBe(true)
})

test('hides the dialog when the warning was already dismissed', () => {
  mockCookie.mockReturnValue(cookieWithDismissed('changes-info'))

  const { isShown } = renderDismissDialog('changes-info')

  expect(isShown.value).toBe(false)
})

test('dismiss() hides the dialog and persists the dismissal to the server', async () => {
  const { isShown, dismiss } = renderDismissDialog('changes-info')
  expect(isShown.value).toBe(true)

  await dismiss()

  expect(isShown.value).toBe(false)
  expect(fetchMock).toHaveBeenCalledOnce()
  const [url, init] = fetchMock.mock.calls[0]! as [string, RequestInit]
  expect(url).toBe(DISMISS_ENDPOINT)
  expect(init.method).toBe('POST')
  expect(init.body).toBe(JSON.stringify({ warning: 'changes-info' }))
})

test('persists isShown semantics (not inverted) to sessionStorage on dismiss', async () => {
  const { dismiss } = renderDismissDialog('changes-info')

  await nextTick()
  expect(sessionStorage.getItem('changes-info')).toBe('true')

  await dismiss()
  await nextTick()

  expect(sessionStorage.getItem('changes-info')).toBe('false')
})

test('onMounted overrides a stale sessionStorage value left by the old CmkDialog', () => {
  sessionStorage.setItem('changes-info', 'true')
  mockCookie.mockReturnValue(cookieWithDismissed('changes-info'))

  const { isShown } = renderDismissDialog('changes-info')

  expect(isShown.value).toBe(false)
})

test('always shown and never persisted when no key is provided', async () => {
  mockCookie.mockReturnValue(cookieWithDismissed('changes-info'))

  const { isShown, dismiss } = renderDismissDialog(undefined)
  expect(isShown.value).toBe(true)

  await dismiss()

  expect(isShown.value).toBe(false)
  expect(fetchMock).not.toHaveBeenCalled()
})
