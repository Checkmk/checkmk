/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

import ContextualLinkTargetPicker from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkTargetPicker.vue'
import type { VisualLocation } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'

const API = `${location.protocol}//${location.host}/api/internal`

function dashboard(name: string, title: string, owner: string | null = null) {
  return {
    domainType: 'dashboard_metadata',
    id: name,
    links: [],
    extensions: {
      name,
      owner,
      is_built_in: true,
      is_editable: false,
      layout_type: 'relative_grid',
      display: { title }
    }
  }
}

useMswServer(
  // Asked for all owners, the list holds every copy, such as another user's.
  http.get(`${API}/domain-types/dashboard_metadata/collections/all`, ({ request }) => {
    const allOwners = new URL(request.url).searchParams.get('all_owners') === 'true'
    const copies = [dashboard('main', 'Overview'), dashboard('host', 'Host details')]
    return HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: 'all',
      links: [],
      value: allOwners ? [...copies, dashboard('main', 'Overview', 'harry')] : copies
    })
  }),
  // The views selector lists the views and their data sources.
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({ domainType: 'view', id: 'all', links: [], value: [] })
  ),
  http.get(`${API}/objects/constant/data_source/collections/all`, () =>
    HttpResponse.json({ domainType: 'constant', id: 'data_source', links: [], value: [] })
  )
)

function renderPicker(target: VisualLocation) {
  render(ContextualLinkTargetPicker, { props: { modelValue: target } })
  return screen.findByRole('combobox', { name: 'Select a target' })
}

describe('ContextualLinkTargetPicker', () => {
  it('offers every listed dashboard by its title and name', async () => {
    const dropdown = await renderPicker({ type: 'dashboards', name: 'main' })
    await waitFor(() => expect(dropdown).toHaveTextContent('Overview (main)'))

    await userEvent.setup().click(dropdown)
    const options = await screen.findAllByRole('option')

    expect(options.map((option) => option.textContent)).toEqual([
      'Host details (host)',
      'Overview (main)'
    ])
  })

  it('labels a stored dashboard that is no longer listed by its name', async () => {
    const dropdown = await renderPicker({ type: 'dashboards', name: 'gone' })

    await waitFor(() => expect(dropdown).toHaveTextContent('gone'))
  })

  it('clears the target when the category changes, so no hidden target is saved', async () => {
    const { emitted } = render(ContextualLinkTargetPicker, {
      props: { modelValue: { type: 'views', name: 'allhosts' } }
    })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('combobox', { name: 'Select a category' }))
    await user.click(await screen.findByRole('option', { name: 'Dashboards' }))

    expect(emitted('update:modelValue')).toEqual([[null]])
  })
})
