/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { CmkFetchError } from '@/lib/cmkFetch'

import AccessSettings from '@/dashboard/components/Wizard/wizards/dashboard-settings/components/AccessSettings.vue'
import type { DashboardShare } from '@/dashboard/types/shared'

import { flushPromises, wrapInSuspense } from '../../../../utils.ts'

const mockGetContactGroups = vi.hoisted(() =>
  vi.fn().mockResolvedValue([
    { name: 'admins', title: 'Administrators' },
    { name: 'operators', title: 'Operators' }
  ])
)

const mockGetSites = vi.hoisted(() =>
  vi.fn().mockResolvedValue([
    { name: 'site1', title: 'Site 1' },
    { name: 'site2', title: 'Site 2' }
  ])
)

vi.mock('@/dashboard/components/Wizard/wizards/dashboard-settings/api', () => ({
  getContactGroups: mockGetContactGroups,
  getSites: mockGetSites
}))

async function renderAccessSettings(share: DashboardShare = 'no', errors: string[] = []) {
  const shareRef = ref(share)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(AccessSettings, {
          share: shareRef.value,
          'onUpdate:share': (v: DashboardShare) => (shareRef.value = v),
          errors
        })
    }
  })

  render(wrapInSuspense(wrapper, { props: {} }))
  await flushPromises()
  return { shareRef }
}

function getToggleButton(label: string): HTMLButtonElement {
  return screen.getByRole('button', { name: `Toggle ${label}` }) as HTMLButtonElement
}

describe('AccessSettings', () => {
  // Vue emits a console.info for <Suspense> being experimental; silence it for fail-on-console.
  beforeEach(() => {
    vi.spyOn(console, 'info').mockImplementation(() => {})
  })

  describe('Rendering', () => {
    it('renders the toggle button group with all share options', async () => {
      await renderAccessSettings()
      expect(getToggleButton('Owner (private)')).toBeInTheDocument()
      expect(getToggleButton('All users')).toBeInTheDocument()
      expect(getToggleButton('Members of contact groups')).toBeInTheDocument()
      expect(getToggleButton('Users of site')).toBeInTheDocument()
    })

    it('does not render the dual list when share mode is "no"', async () => {
      await renderAccessSettings('no')
      expect(screen.queryByRole('group', { name: 'Visual information' })).not.toBeInTheDocument()
    })

    it('does not render the dual list when share mode is "with_all_users"', async () => {
      await renderAccessSettings({ type: 'with_all_users' })
      expect(screen.queryByRole('group', { name: 'Visual information' })).not.toBeInTheDocument()
    })
  })

  describe('Contact groups loading', () => {
    it('fetches contact groups on mount', async () => {
      await renderAccessSettings()
      expect(mockGetContactGroups).toHaveBeenCalled()
    })

    it('disables the contact groups option when getContactGroups returns empty', async () => {
      mockGetContactGroups.mockResolvedValueOnce([])
      await renderAccessSettings()
      expect(getToggleButton('Members of contact groups')).toBeDisabled()
    })
  })

  describe('Share mode with_contact_groups', () => {
    it('renders dual list with available contact groups', async () => {
      await renderAccessSettings({
        type: 'with_contact_groups',
        contact_groups: ['admins']
      })
      const dualList = screen.getByRole('group', { name: 'Visual information' })
      expect(dualList).toBeInTheDocument()
      expect(within(dualList).getByText('Administrators')).toBeInTheDocument()
      expect(within(dualList).getByText('Operators')).toBeInTheDocument()
    })
  })

  describe('Share mode with_sites', () => {
    it('renders dual list with available sites', async () => {
      await renderAccessSettings({ type: 'with_sites', sites: ['site1'] })
      const dualList = screen.getByRole('group', { name: 'Visual information' })
      expect(dualList).toBeInTheDocument()
      expect(within(dualList).getByText('Site 1')).toBeInTheDocument()
      expect(within(dualList).getByText('Site 2')).toBeInTheDocument()
    })
  })

  describe('Error display', () => {
    it('renders inline validation when errors are present and dual list is visible', async () => {
      await renderAccessSettings({ type: 'with_contact_groups', contact_groups: [] }, [
        'Selection required'
      ])
      expect(screen.getByText('Selection required')).toBeInTheDocument()
    })

    it('does not render inline validation when there are no errors', async () => {
      await renderAccessSettings({ type: 'with_contact_groups', contact_groups: [] }, [])
      expect(screen.queryByText('Selection required')).not.toBeInTheDocument()
    })
  })

  describe('API error handling', () => {
    it('disables contact groups option on 403 from getContactGroups', async () => {
      mockGetContactGroups.mockRejectedValueOnce(new CmkFetchError('Forbidden', null, '', 403))
      await renderAccessSettings()
      expect(getToggleButton('Members of contact groups')).toBeDisabled()
    })

    it('disables contact groups option on 401 from getContactGroups', async () => {
      mockGetContactGroups.mockRejectedValueOnce(new CmkFetchError('Unauthorized', null, '', 401))
      await renderAccessSettings()
      expect(getToggleButton('Members of contact groups')).toBeDisabled()
    })

    it('clears available elements on 403 from getSites during loadAvailableElements', async () => {
      mockGetSites.mockRejectedValueOnce(new CmkFetchError('Forbidden', null, '', 403))
      await renderAccessSettings({ type: 'with_sites', sites: [] })
      const dualList = screen.getByRole('group', { name: 'Visual information' })
      expect(within(dualList).queryByText('Site 1')).not.toBeInTheDocument()
      expect(within(dualList).queryByText('Site 2')).not.toBeInTheDocument()
    })
  })

  describe('Share mode switching', () => {
    it('shows dual list when switching from "no" to "with_contact_groups"', async () => {
      await renderAccessSettings('no')
      await fireEvent.click(getToggleButton('Members of contact groups'))
      await flushPromises()
      expect(screen.getByRole('group', { name: 'Visual information' })).toBeInTheDocument()
    })

    it('hides dual list when switching from "with_contact_groups" to "no"', async () => {
      await renderAccessSettings({ type: 'with_contact_groups', contact_groups: [] })
      await fireEvent.click(getToggleButton('Owner (private)'))
      await flushPromises()
      expect(screen.queryByRole('group', { name: 'Visual information' })).not.toBeInTheDocument()
    })

    it('updates share model when switching to "with_all_users"', async () => {
      const { shareRef } = await renderAccessSettings('no')
      await fireEvent.click(getToggleButton('All users'))
      await flushPromises()
      expect(shareRef.value).toEqual({ type: 'with_all_users' })
    })
  })
})
