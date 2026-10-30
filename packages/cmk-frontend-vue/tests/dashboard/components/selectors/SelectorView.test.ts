/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitForElementToBeRemoved } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

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

const ALLHOSTS = view('allhosts', 'All hosts', 'harry')
const HOST_VIEW = view('host', 'Single host', '', ['host'])
const SERVICE_VIEW = view('service', 'Single service', '', ['service', 'host'])

useMswServer(
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({
      domainType: 'view',
      id: 'all',
      links: [],
      value: [ALLHOSTS, HOST_VIEW, SERVICE_VIEW]
    })
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
  it('hands up the name of the picked view', async () => {
    const { emitted } = render(SelectorView, { props: { readOnly: false, selectedView: null } })
    await waitForElementToBeRemoved(await screen.findByText('Loading...'))
    const user = userEvent.setup()

    await user.click(screen.getByRole('combobox', { name: 'Select view' }))
    await user.click(await screen.findByRole('option', { name: 'Hosts - All hosts (allhosts)' }))

    expect(emitted('update:selectedView')).toEqual([['allhosts']])
  })

  it('offers the views that show a single object', async () => {
    const options = await openedOptions({})

    expect(options).toEqual([
      'Hosts - All hosts (allhosts)',
      'Hosts - Single host (host)',
      'Hosts - Single service (service)'
    ])
  })

  it('labels a stored view that is no longer listed by its name', async () => {
    const dropdown = await renderLoaded({ selectedView: 'gone' })

    expect(dropdown).toHaveTextContent('gone')
  })
})
