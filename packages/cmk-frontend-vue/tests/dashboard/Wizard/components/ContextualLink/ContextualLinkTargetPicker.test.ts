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
import { defineComponent, h, ref } from 'vue'

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
      is_built_in: owner === null,
      is_editable: false,
      layout_type: 'relative_grid',
      display: { title }
    }
  }
}

function view(name: string, title: string, owner = '') {
  return {
    domainType: 'view',
    id: name,
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

useMswServer(
  // Asked for all owners, the list holds every copy, such as another user's.
  http.get(`${API}/domain-types/dashboard_metadata/collections/all`, ({ request }) => {
    const allOwners = new URL(request.url).searchParams.get('all_owners') === 'true'
    const copies = [dashboard('main', 'Overview'), dashboard('mine', 'My hosts', 'cmkadmin')]
    return HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: 'all',
      links: [],
      value: allOwners ? [...copies, dashboard('main', 'Overview', 'harry')] : copies
    })
  }),
  http.get(`${API}/domain-types/view/collections/all`, () =>
    HttpResponse.json({
      domainType: 'view',
      id: 'all',
      links: [],
      value: [view('allhosts', 'All hosts')]
    })
  )
)

const user = userEvent.setup()

async function openPicker(stored: VisualLocation | null) {
  const target = ref(stored)
  render(
    defineComponent({
      setup: () => () =>
        h(ContextualLinkTargetPicker, {
          modelValue: target.value,
          'onUpdate:modelValue': (value: VisualLocation | null) => (target.value = value)
        })
    })
  )
  const trigger = screen.getByRole('button', { name: /^Target page/ })
  // Both lists are loaded once the menu holds the view and both dashboards.
  await user.click(trigger)
  await waitFor(() => expect(screen.getAllByRole('menuitem')).toHaveLength(3))
  return trigger
}

function itemNames(): (string | null)[] {
  return screen.getAllByRole('menuitem').map((item) => item.getAttribute('aria-label'))
}

describe('ContextualLinkTargetPicker', () => {
  it('offers the dashboards and the views by title and name, each built-in or custom', async () => {
    await openPicker(null)

    expect(itemNames()).toEqual([
      'My hosts – mine – Custom',
      'Overview – main – Built-in',
      'All hosts – allhosts – Built-in'
    ])
  })

  it('narrows the targets to the views', async () => {
    await openPicker(null)

    await user.click(screen.getByRole('button', { name: 'Toggle View (1)' }))

    expect(itemNames()).toEqual(['All hosts – allhosts – Built-in'])
  })

  it('picks a view as the target', async () => {
    await openPicker(null)

    await user.click(screen.getByRole('menuitem', { name: 'All hosts – allhosts – Built-in' }))

    expect(screen.getByRole('button', { name: 'Target page: All hosts' })).toBeInTheDocument()
  })

  it('picks a dashboard as the target', async () => {
    await openPicker({ type: 'views', name: 'allhosts' })

    await user.click(screen.getByRole('menuitem', { name: 'Overview – main – Built-in' }))

    expect(screen.getByRole('button', { name: 'Target page: Overview' })).toBeInTheDocument()
  })

  it('shows the stored target by its title', async () => {
    const trigger = await openPicker({ type: 'dashboards', name: 'main' })

    expect(trigger).toHaveTextContent('Overview')
  })

  it('shows a stored target that is no longer listed by its name', async () => {
    const trigger = await openPicker({ type: 'dashboards', name: 'gone' })

    expect(trigger).toHaveTextContent('gone')
  })
})
