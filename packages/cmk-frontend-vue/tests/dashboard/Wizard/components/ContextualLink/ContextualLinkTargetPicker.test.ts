/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import ContextualLinkTargetPicker from '@/dashboard/components/Wizard/components/ContextualLink/ContextualLinkTargetPicker.vue'
import type { VisualLocation } from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useLinkTargets } from '@/dashboard/components/Wizard/components/ContextualLink/useLinkTargets'
import type { ViewModel } from '@/dashboard/types/api'

import {
  dashboardMetadata,
  dashboardMetadataListHandler,
  viewsHandler
} from '@tests/dashboard/apiHandlers'

function view(name: string, title: string, owner = ''): ViewModel {
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

const COPIES = [
  dashboardMetadata('main', 'Overview', null),
  dashboardMetadata('mine', 'My hosts', 'cmkadmin')
]

useMswServer(
  dashboardMetadataListHandler(COPIES, { allOwners: false }),
  // Asked for all owners, the list holds every copy, such as another user's.
  dashboardMetadataListHandler([...COPIES, dashboardMetadata('main', 'Overview', 'harry')], {
    allOwners: true
  }),
  viewsHandler([view('allhosts', 'All hosts')])
)

const user = userEvent.setup()

async function openPicker(stored: VisualLocation | null) {
  const target = ref(stored)
  render(
    defineComponent({
      setup() {
        const { targets, viewsError, dashboardsError, load } = useLinkTargets()
        void load()
        return () =>
          h(ContextualLinkTargetPicker, {
            targets: targets.value,
            viewsError: viewsError.value,
            dashboardsError: dashboardsError.value,
            modelValue: target.value,
            'onUpdate:modelValue': (value: VisualLocation | null) => (target.value = value)
          })
      }
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
