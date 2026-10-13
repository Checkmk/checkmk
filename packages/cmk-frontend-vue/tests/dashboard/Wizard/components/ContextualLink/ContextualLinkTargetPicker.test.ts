/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'

import ContextualLinkTargetPicker from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkTargetPicker.vue'
import type { VisualLocation } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'

const API = `${location.protocol}//${location.host}/api/internal`

function dashboard(name: string, title: string, restrictedToSingle: string[]) {
  return {
    domainType: 'dashboard_metadata',
    id: name,
    links: [],
    extensions: {
      name,
      owner: null,
      is_built_in: true,
      is_editable: false,
      layout_type: 'relative_grid',
      restricted_to_single: restrictedToSingle,
      display: { title }
    }
  }
}

useMswServer(
  http.get(`${API}/domain-types/dashboard_metadata/collections/all`, () =>
    HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: 'all',
      links: [],
      value: [dashboard('main', 'Overview', []), dashboard('host', 'Host details', ['host'])]
    })
  ),
  // The views selector lists the views and their data sources.
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({ domainType: 'view', id: 'all', links: [], value: [] })
  ),
  http.get(`${API}/objects/constant/data_source/collections/all`, () =>
    HttpResponse.json({ domainType: 'constant', id: 'data_source', links: [], value: [] })
  )
)

function renderPicker(target: VisualLocation, singleInfos: string[]) {
  render(ContextualLinkTargetPicker, { props: { modelValue: target, singleInfos } })
  return screen.findByRole('combobox', { name: 'Select a target' })
}

describe('ContextualLinkTargetPicker', () => {
  it('offers only the dashboards a click can fill', async () => {
    const dropdown = await renderPicker({ type: 'dashboards', name: 'main', owner: '' }, [])
    await waitFor(() => expect(dropdown).toHaveTextContent('Overview'))

    await userEvent.setup().click(dropdown)
    const options = await screen.findAllByRole('option')

    expect(options.map((option) => option.textContent)).toEqual(['Overview'])
  })

  it('labels a stored dashboard copy that is no longer listed by its name and owner', async () => {
    const dropdown = await renderPicker({ type: 'dashboards', name: 'gone', owner: 'harry' }, [])

    await waitFor(() => expect(dropdown).toHaveTextContent('gone (harry)'))
  })

  it('labels a stored dashboard without owner as resolved by name', async () => {
    const dropdown = await renderPicker({ type: 'dashboards', name: 'main', owner: null }, [])

    await waitFor(() => expect(dropdown).toHaveTextContent('main (resolved by name)'))
  })

  it('clears the target when the category changes, so no hidden target is saved', async () => {
    const { emitted } = render(ContextualLinkTargetPicker, {
      props: { modelValue: { type: 'views', name: 'allhosts', owner: null }, singleInfos: [] }
    })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('combobox', { name: 'Select a category' }))
    await user.click(await screen.findByRole('option', { name: 'Dashboards' }))

    expect(emitted('update:modelValue')).toEqual([[null]])
  })
})
