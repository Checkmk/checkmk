/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import type { DismissableWarning } from 'cmk-ui-library/lib/userConfig'
import { type MockInstance, afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'

const DISMISS_ENDPOINT = '/domain-types/user_config/actions/dismiss-warning/invoke'

const mockCookie = vi.fn()
let postSpy: MockInstance<typeof client.POST>

beforeAll(() => {
  Object.defineProperty(document, 'cookie', { get: mockCookie, configurable: true })
})

beforeEach(() => {
  sessionStorage.clear()
  mockCookie.mockReturnValue('')
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: undefined,
    error: undefined,
    response: new Response(null, { status: 204 })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function cookieWithDismissed(...warnings: string[]): string {
  const value = encodeURIComponent(JSON.stringify({ dismissed_warnings: warnings }))
  return `user_frontend_config=${value}`
}

function renderDismissDialog(key: DismissableWarning | undefined) {
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
  expect(postSpy).toHaveBeenCalledOnce()
  expect(postSpy).toHaveBeenCalledWith(DISMISS_ENDPOINT, {
    params: { header: { 'Content-Type': 'application/json' } },
    body: { warning: 'changes-info' }
  })
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
  expect(postSpy).not.toHaveBeenCalled()
})
