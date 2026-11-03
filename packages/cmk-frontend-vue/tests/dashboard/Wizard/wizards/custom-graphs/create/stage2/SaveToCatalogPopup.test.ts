/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { describe, expect, test, vi } from 'vitest'

import SaveToCatalogPopup from '@/dashboard/components/Wizard/wizards/custom-graphs/create/stage2/SaveToCatalogPopup.vue'
import type { EmbeddedGraphDefinition } from '@/dashboard/components/Wizard/wizards/custom-graphs/editor/types'

const CREATE_PATH = '/domain-types/custom_graph/collections/all'

const DEFINITION = {
  data_sources: [],
  graph_options: {
    unit: { type: 'first_entry_with_unit' },
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: true
  }
} as unknown as EmbeddedGraphDefinition

function ok(data: unknown): never {
  return { data, error: undefined, response: new Response(null, { status: 200 }) } as never
}

function catalogWith(...names: string[]) {
  vi.spyOn(client, 'GET').mockResolvedValue(
    ok({ value: names.map((id) => ({ id, title: id, extensions: { owner: 'admin' } })) })
  )
}

function renderPopup(nameBase?: string) {
  const onSaved = vi.fn()
  render(SaveToCatalogPopup, { props: { definition: DEFINITION, nameBase, edit: false, onSaved } })
  return { onSaved }
}

async function idInput(): Promise<HTMLInputElement> {
  const input = await screen.findByRole<HTMLInputElement>('textbox', {
    name: 'Unique ID (required)'
  })
  await waitFor(() => expect(input.value).not.toBe(''))
  return input
}

describe('SaveToCatalogPopup', () => {
  test('suggests the given base while no graph has it', async () => {
    catalogWith('cpu')

    renderPopup('cpu_clone')

    expect((await idInput()).value).toBe('cpu_clone')
  })

  test('numbers the given base once a graph has it', async () => {
    catalogWith('cpu_clone', 'cpu_clone_1')

    renderPopup('cpu_clone')

    expect((await idInput()).value).toBe('cpu_clone_2')
  })

  test('suggests the next free default ID without a base', async () => {
    catalogWith('custom_graph_1')

    renderPopup()

    expect((await idInput()).value).toBe('custom_graph_2')
  })

  test('saves the graph privately under the entered title and ID', async () => {
    catalogWith()
    const postSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce({
      data: { id: 'custom_graph_1' },
      error: undefined,
      response: new Response(null, { status: 200, headers: { ETag: '"1"' } })
    } as never)
    const { onSaved } = renderPopup()
    await idInput()

    await userEvent.type(screen.getByRole('textbox', { name: 'Title (required)' }), ' My graph ')
    await userEvent.click(screen.getByRole('button', { name: 'Save to catalog & place widget' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith('custom_graph_1'))
    expect(postSpy).toHaveBeenCalledWith(CREATE_PATH, {
      params: { header: { 'Content-Type': 'application/json' } },
      body: {
        name: 'custom_graph_1',
        title: 'My graph',
        metadata: {
          description: '',
          topic: 'my_workplace',
          sort_index: 99,
          hidden: false,
          is_show_more: false,
          public: { type: 'private' }
        },
        content: DEFINITION
      }
    })
  })

  test('flags an ID the user already has when saving', async () => {
    catalogWith()
    vi.spyOn(client, 'POST').mockResolvedValueOnce({
      data: undefined,
      error: { title: 'Custom graph already exists', detail: 'Taken.' },
      response: new Response('', { status: 409, statusText: 'Conflict' })
    } as never)
    const { onSaved } = renderPopup()
    await idInput()

    await userEvent.type(screen.getByRole('textbox', { name: 'Title (required)' }), 'My graph')
    await userEvent.click(screen.getByRole('button', { name: 'Save to catalog & place widget' }))

    expect(await screen.findByText('You already have a custom graph with this ID.')).toBeVisible()
    expect(onSaved).not.toHaveBeenCalled()
  })

  test('does not save without a title', async () => {
    catalogWith()
    const postSpy = vi.spyOn(client, 'POST')
    renderPopup()
    await idInput()

    await userEvent.click(screen.getByRole('button', { name: 'Save to catalog & place widget' }))

    expect(await screen.findByText('Enter a title.')).toBeVisible()
    expect(postSpy).not.toHaveBeenCalled()
  })

  test('flags an ID that does not start with a letter or an underscore', async () => {
    catalogWith()
    renderPopup()
    const input = await idInput()

    await userEvent.clear(input)
    await userEvent.type(input, '1graph')

    expect(
      await screen.findByText(
        'Start with a letter or an underscore, then use only letters, digits, hyphens (-) and underscores (_).'
      )
    ).toBeVisible()
  })
})
