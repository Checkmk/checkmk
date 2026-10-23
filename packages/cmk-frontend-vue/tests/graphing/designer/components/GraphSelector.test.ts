/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import GraphSelector, {
  type SelectableGraph
} from '@/graphing/designer/components/GraphSelector.vue'

const SELECTED: SelectableGraph = { name: 'my_graph', owner: 'me', title: 'My graph' }

function entry(id: string | undefined, title: string, owner: string): unknown {
  return { id, title, extensions: { owner } }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getSpy: any

beforeEach(() => {
  getSpy = vi.spyOn(client, 'GET')
})

function mockCollection(entries: unknown[]): void {
  getSpy.mockResolvedValue({
    data: { domainType: 'custom_graph_metadata', value: entries, links: [] },
    error: undefined,
    response: new Response(null, { status: 200 })
  })
}

async function renderSelector() {
  const utils = render(GraphSelector, { props: { selected: SELECTED, loggedInUser: 'me' } })
  await waitFor(() => expect(getSpy).toHaveBeenCalled())
  return utils
}

test('splits own and published graphs into sorted sections, dropping entries without id', async () => {
  mockCollection([
    entry('zeta', 'Zeta', 'me'),
    entry('their_graph', 'Their graph', 'other'),
    entry('alpha', 'Alpha', 'me'),
    entry(undefined, 'Unsaved', 'me')
  ])
  await renderSelector()
  await fireEvent.click(screen.getByRole('combobox', { name: 'Select custom graph' }))

  expect(await screen.findByText('My custom graphs')).toBeInTheDocument()
  expect(screen.getByText('Published custom graphs')).toBeInTheDocument()
  const options = screen
    .getAllByRole('option')
    .map((option) => option.textContent?.replace(/\s+/g, ' ').trim())
  expect(options).toEqual(['Alpha', 'Zeta', 'Their graph (other)'])
})

test('selecting a published graph emits it', async () => {
  mockCollection([entry('their_graph', 'Their graph', 'other')])
  const { emitted } = await renderSelector()
  await fireEvent.click(screen.getByRole('combobox', { name: 'Select custom graph' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Their graph (other)' }))

  expect(emitted('graph-change')).toEqual([
    [{ name: 'their_graph', owner: 'other', title: 'Their graph' }]
  ])
})

test('a failing list request degrades to an explicit empty state', async () => {
  getSpy.mockResolvedValue({
    data: undefined,
    error: { title: 'Internal Server Error' },
    response: new Response('', { status: 500 })
  })
  await renderSelector()
  await fireEvent.click(screen.getByRole('combobox', { name: 'Select custom graph' }))

  expect(await screen.findByText('Failed to load the custom graphs')).toBeInTheDocument()
  expect(screen.queryByRole('option')).not.toBeInTheDocument()
})
