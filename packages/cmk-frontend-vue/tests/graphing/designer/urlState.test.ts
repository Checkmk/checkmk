/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test, vi } from 'vitest'

import { pushUrlState, replaceUrlState } from '@/graphing/designer/urlState'

test('replaceUrlState rewrites name, owner and the edit mode without a history entry', () => {
  const replaceSpy = vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
  replaceUrlState({ name: 'my_graph', owner: 'admin', mode: 'edit' })
  const url = replaceSpy.mock.calls[0]![2] as URL
  expect(url.searchParams.get('name')).toBe('my_graph')
  expect(url.searchParams.get('owner')).toBe('admin')
  expect(url.searchParams.get('mode')).toBe('edit')
})

test('view mode drops the mode parameter', () => {
  const replaceSpy = vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
  replaceUrlState({ name: 'my_graph', owner: 'admin', mode: 'view' })
  const url = replaceSpy.mock.calls[0]![2] as URL
  expect(url.searchParams.has('mode')).toBe(false)
})

test('pushUrlState adds a history entry for a graph switch', () => {
  const pushSpy = vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
  pushUrlState({ name: 'other_graph', owner: 'someone', mode: 'view' })
  const url = pushSpy.mock.calls[0]![2] as URL
  expect(url.searchParams.get('name')).toBe('other_graph')
  expect(url.searchParams.get('owner')).toBe('someone')
})
