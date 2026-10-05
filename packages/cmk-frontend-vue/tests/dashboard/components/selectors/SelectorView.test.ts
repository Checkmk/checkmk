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

function view(id: string, title: string, owner: string, single: string[] = []): ViewModel {
  return {
    domainType: 'view',
    id,
    title,
    links: [],
    extensions: {
      data_source: 'hosts',
      restricted_to_single: single,
      filters: {},
      is_mobile: false,
      owner
    }
  }
}

const BUILT_IN_ALLHOSTS = view('allhosts', 'All hosts', '')
const OWN_ALLHOSTS = view('allhosts', 'All hosts', 'harry')
const HOST_VIEW = view('host', 'Single host', '', ['host'])
const SERVICE_VIEW = view('service', 'Single service', '', ['service', 'host'])

const server = setupServer(
  http.get(`${API}/domain-types/view/collections/all`, ({ request }) => {
    const allOwners = new URL(request.url).searchParams.get('all_owners') === 'true'
    return HttpResponse.json({
      domainType: 'view',
      id: 'all',
      links: [],
      value: allOwners
        ? [BUILT_IN_ALLHOSTS, OWN_ALLHOSTS, HOST_VIEW, SERVICE_VIEW]
        : [OWN_ALLHOSTS, HOST_VIEW, SERVICE_VIEW]
    })
  }),
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

async function openedOptions(props: Record<string, unknown>): Promise<string[]> {
  const user = userEvent.setup()
  await user.click(await renderLoaded(props))
  return (await screen.findAllByRole('option')).map((option) => option.textContent ?? '')
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

  it('offers the built-in copy beside the own copy when keyed by owner', async () => {
    const options = await openedOptions({ byOwner: true })

    expect(options).toContain('Hosts - All hosts (allhosts)')
    expect(options).toContain('Hosts - All hosts (allhosts) (harry)')
  })

  it('offers no single-object view to a click that names no object', async () => {
    const options = await openedOptions({ singleInfos: [] })

    expect(options).toEqual(['Hosts - All hosts (allhosts)'])
  })

  it('offers a single-host view but no single-service view to a click that names a host', async () => {
    const options = await openedOptions({ singleInfos: ['host'] })

    expect(options).toEqual(['Hosts - All hosts (allhosts)', 'Hosts - Single host (host)'])
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
