/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavPage } from '@ucl/_ucl/composables/useNavigation'
import { createPageStatus } from '@ucl/_ucl/composables/usePageStatus'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'

const dismissedChipsStorageKey = 'ucl-dismissed-status-chips'

const component = defineComponent({
  props: { screenshotMode: { type: Boolean, required: true } },
  template: '<div/>'
})

const freshPage: NavPage = {
  type: 'page',
  name: 'Fresh',
  path: '/components/fresh',
  component,
  status: 'new',
  statusSince: '2026-01-01'
}

const oldPage: NavPage = {
  type: 'page',
  name: 'Old',
  path: '/components/old',
  component,
  status: 'deprecated'
}

const pages = [freshPage, oldPage]

function storedDismissals(): string[] {
  return JSON.parse(localStorage.getItem(dismissedChipsStorageKey) ?? '[]')
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'], now: new Date('2026-01-15') })
})

afterEach(() => {
  localStorage.removeItem(dismissedChipsStorageKey)
  vi.useRealTimers()
})

test('shows a new chip of a page that was not visited', () => {
  const { visibleStatus } = createPageStatus(pages)

  expect(visibleStatus(freshPage)).toBe('new')
})

test('hides a new chip once its page is visited', () => {
  const { visibleStatus, dismissStatusForPath } = createPageStatus(pages)

  dismissStatusForPath(freshPage.path)

  expect(visibleStatus(freshPage)).toBeUndefined()
})

test('keeps a deprecated chip after its page is visited', () => {
  const { visibleStatus, dismissStatusForPath } = createPageStatus(pages)

  dismissStatusForPath(oldPage.path)

  expect(visibleStatus(oldPage)).toBe('deprecated')
})

test('hides a new chip 90 days after its status was set', () => {
  const { visibleStatus } = createPageStatus(pages)

  vi.setSystemTime(new Date('2026-04-02'))

  expect(visibleStatus(freshPage)).toBeUndefined()
})

test('remembers a dismissal across reloads', async () => {
  createPageStatus(pages).dismissStatusForPath(freshPage.path)
  await nextTick()

  const { visibleStatus } = createPageStatus(pages)

  expect(visibleStatus(freshPage)).toBeUndefined()
})

test('drops stored dismissals that no page produces any more', async () => {
  localStorage.setItem(dismissedChipsStorageKey, JSON.stringify(['a page that was removed']))

  createPageStatus(pages)
  await nextTick()

  expect(storedDismissals()).toEqual([])
})
