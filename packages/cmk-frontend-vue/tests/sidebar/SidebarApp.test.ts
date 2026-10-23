/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { beforeEach, expect, vi } from 'vitest'

import SidebarApp from '@/sidebar/SidebarApp.vue'

useMswServer(
  http.get('*/sidebar_snapin.py', () =>
    HttpResponse.json(['<input id="mk_side_search_field" type="text" />'])
  )
)

beforeEach(() => {
  // the legacy global is only stubbed for the snapin content hook
  vi.stubGlobal('cmk', { utils: { execute_javascript_by_object: () => {} } })
})

async function renderSidebarWithQuicksearch(): Promise<{
  snapin: HTMLElement
  searchField: HTMLElement
}> {
  render(SidebarApp, {
    props: {
      snapins: [{ name: 'quicksearch', title: 'Quick search', open: true }],
      update_interval: 30
    }
  })

  const snapin = await waitFor(() => {
    const element = document.getElementById('snapin_quicksearch')
    expect(element).not.toBeNull()
    return element!
  })
  const searchField = await waitFor(() => {
    const element = document.getElementById('mk_side_search_field')
    expect(element).not.toBeNull()
    return element!
  })
  return { snapin, searchField }
}

test('a snapin stays draggable while the pointer is pressed outside an input', async () => {
  const { snapin } = await renderSidebarWithQuicksearch()

  await userEvent.pointer({ target: snapin, keys: '[MouseLeft>]' })

  expect(snapin).toHaveAttribute('draggable', 'true')
})

test('a snapin is not draggable while the pointer is pressed on an input', async () => {
  const { snapin, searchField } = await renderSidebarWithQuicksearch()

  await userEvent.pointer({ target: searchField, keys: '[MouseLeft>]' })

  expect(snapin).toHaveAttribute('draggable', 'false')
})

test('a snapin becomes draggable again once the pointer is released', async () => {
  const { snapin, searchField } = await renderSidebarWithQuicksearch()

  await userEvent.pointer([{ target: searchField, keys: '[MouseLeft>]' }, { keys: '[/MouseLeft]' }])

  expect(snapin).toHaveAttribute('draggable', 'true')
})
