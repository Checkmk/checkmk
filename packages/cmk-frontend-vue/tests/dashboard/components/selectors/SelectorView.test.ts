/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitForElementToBeRemoved } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'

import SelectorView from '@/dashboard/components/selectors/SelectorView.vue'
import type { ViewModel } from '@/dashboard/types/api'

const API = `${location.protocol}//${location.host}/api/internal`

function view(id: string, title: string, owner: string): ViewModel {
  return {
    domainType: 'view',
    id,
    title,
    links: [],
    extensions: {
      data_source: 'hosts',
      restricted_to_single: [],
      filters: {},
      is_mobile: false,
      owner
    }
  }
}

const OWN_ALLHOSTS = view('allhosts', 'All hosts', 'harry')

const server = setupServer(
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({ domainType: 'view', id: 'all', links: [], value: [OWN_ALLHOSTS] })
  ),
  http.get(`${API}/objects/constant/data_source/collections/all`, () =>
    HttpResponse.json({
      domainType: 'constant',
      id: 'data_source',
      links: [],
      value: [
        {
          domainType: 'constant',
          id: 'hosts',
          title: 'Hosts',
          links: [],
          extensions: { infos: ['host'] }
        }
      ]
    })
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

async function renderLoaded(props: Record<string, unknown>): Promise<HTMLElement> {
  render(SelectorView, { props: { readOnly: false, selectedView: null, ...props } })
  await waitForElementToBeRemoved(await screen.findByText('Loading...'))
  return screen.getByRole('combobox', { name: 'Select view' })
}

describe('SelectorView', () => {
  it('hands up the picked copy with its owner', async () => {
    const { emitted } = render(SelectorView, {
      props: { readOnly: false, byOwner: true, selectedCopy: null }
    })
    await waitForElementToBeRemoved(await screen.findByText('Loading...'))
    const user = userEvent.setup()

    await user.click(screen.getByRole('combobox', { name: 'Select view' }))
    await user.click(
      await screen.findByRole('option', { name: 'Hosts - All hosts (allhosts) (harry)' })
    )

    expect(emitted('update:selectedCopy')).toEqual([[{ name: 'allhosts', owner: 'harry' }]])
  })

  it('labels a stored copy that is no longer listed by its name and owner', async () => {
    const dropdown = await renderLoaded({
      byOwner: true,
      selectedCopy: { name: 'gone', owner: 'harry' }
    })

    expect(dropdown).toHaveTextContent('gone (harry)')
  })

  it('labels a stored name without owner as resolved by name', async () => {
    const dropdown = await renderLoaded({
      byOwner: true,
      selectedCopy: { name: 'allhosts', owner: null }
    })

    expect(dropdown).toHaveTextContent('allhosts (resolved by name)')
  })
})
