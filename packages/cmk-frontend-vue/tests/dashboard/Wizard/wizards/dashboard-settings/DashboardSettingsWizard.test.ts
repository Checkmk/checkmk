/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardSettingsWizard from '@/dashboard/components/Wizard/wizards/dashboard-settings/DashboardSettingsWizard.vue'
import type { DashboardGeneralSettings } from '@/dashboard/types/dashboard'

import { flushPromises, wrapInSuspense } from '../../../utils.ts'

const mockListDashboardMetadata = vi.hoisted(() => vi.fn().mockResolvedValue([]))

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    listDashboardMetadata: mockListDashboardMetadata
  }
}))

// Stub GeneralProperties to avoid IconSelector's REST API dependency
vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/GeneralProperties.vue', () => ({
  default: {
    name: 'GeneralProperties',
    template: '<div data-testid="general-properties-stub" />'
  }
}))

function makeGeneralSettings(
  overrides: Partial<DashboardGeneralSettings> = {}
): DashboardGeneralSettings {
  return {
    title: { text: 'My Dashboard', render: true, include_context: false },
    menu: {
      topic: 'monitoring',
      sort_index: 10,
      is_show_more: false,
      search_terms: []
    },
    visibility: {
      hide_in_monitor_menu: false,
      hide_in_drop_down_menus: false,
      share: 'no'
    },
    ...overrides
  }
}

const defaultProps = {
  activeDashboardId: 'my_dashboard',
  dashboardGeneralSettings: makeGeneralSettings(),
  dashboardRestrictedToSingle: [],
  loggedInUser: 'admin'
}

async function renderWizard(
  props: Partial<typeof defaultProps> = {},
  callbacks: {
    onSave?: (...args: unknown[]) => void
    onCancel?: () => void
  } = {}
) {
  const mergedProps = { ...defaultProps, ...props, ...callbacks }
  render(wrapInSuspense(DashboardSettingsWizard, { props: mergedProps }))
  await flushPromises()
}

describe('DashboardSettingsWizard (inner)', () => {
  beforeEach(() => {
    // Vue emits a console.info for <Suspense> being experimental; silence it for fail-on-console.
    vi.spyOn(console, 'info').mockImplementation(() => {})
  })

  describe('Rendering', () => {
    it('renders the heading with the dashboard name', async () => {
      await renderWizard()
      expect(await screen.findByText('Dashboard settings of My Dashboard')).toBeInTheDocument()
    })
  })

  describe('Cancel', () => {
    it('emits "cancel" when the Cancel button is clicked', async () => {
      const onCancel = vi.fn()
      await renderWizard({}, { onCancel })
      await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
      expect(onCancel).toHaveBeenCalledOnce()
    })
  })

  describe('Save validation', () => {
    it('does not emit "save" when the name is empty', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            title: { text: '', render: true, include_context: false }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the name is only whitespace', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            title: { text: '   ', render: true, include_context: false }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the unique ID is empty', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          activeDashboardId: ''
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the unique ID has invalid characters', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          activeDashboardId: 'Invalid-ID'
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the unique ID is already in use', async () => {
      mockListDashboardMetadata.mockResolvedValueOnce([
        { name: 'my_dashboard', owner: 'my_dashboard' }
      ])
      const onSave = vi.fn()
      await renderWizard({}, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the sort index is negative', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            menu: {
              topic: 'monitoring',
              sort_index: -1,
              is_show_more: false,
              search_terms: []
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when the sort index is a float', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            menu: {
              topic: 'monitoring',
              sort_index: 5.5,
              is_show_more: false,
              search_terms: []
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when sharing with contact groups but none selected', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            visibility: {
              hide_in_monitor_menu: false,
              hide_in_drop_down_menus: false,
              share: { type: 'with_contact_groups', contact_groups: [] }
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })

    it('does not emit "save" when sharing with sites but none selected', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            visibility: {
              hide_in_monitor_menu: false,
              hide_in_drop_down_menus: false,
              share: { type: 'with_sites', sites: [] }
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).not.toHaveBeenCalled()
    })
  })

  describe('Save success', () => {
    it('emits "save" with dashboard ID and general settings when all validations pass', async () => {
      const onSave = vi.fn()
      await renderWizard({}, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()

      expect(onSave).toHaveBeenCalledOnce()
      const [dashboardId, settings] = onSave.mock.calls[0]!
      expect(dashboardId).toBe('my_dashboard')
      expect(settings.title.text).toBe('My Dashboard')
    })

    it('emits "save" when share is "with_all_users"', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            visibility: {
              hide_in_monitor_menu: false,
              hide_in_drop_down_menus: false,
              share: { type: 'with_all_users' }
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).toHaveBeenCalledOnce()
    })

    it('emits "save" when share is "with_contact_groups" with groups selected', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            visibility: {
              hide_in_monitor_menu: false,
              hide_in_drop_down_menus: false,
              share: { type: 'with_contact_groups', contact_groups: ['admins'] }
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).toHaveBeenCalledOnce()
    })

    it('emits "save" when share is "with_sites" with sites selected', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            visibility: {
              hide_in_monitor_menu: false,
              hide_in_drop_down_menus: false,
              share: { type: 'with_sites', sites: ['site1'] }
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).toHaveBeenCalledOnce()
    })

    it('trims the unique ID before emitting save', async () => {
      const onSave = vi.fn()
      await renderWizard({ activeDashboardId: '  my_dashboard  ' }, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).toHaveBeenCalledOnce()
      const [dashboardId] = onSave.mock.calls[0]!
      expect(dashboardId).toBe('my_dashboard')
    })
  })

  describe('Icon handling on save', () => {
    it('includes icon in settings when dashboardIcon is set', async () => {
      const onSave = vi.fn()
      const settings = makeGeneralSettings({
        menu: {
          topic: 'monitoring',
          sort_index: 10,
          is_show_more: false,
          search_terms: [],
          icon: { name: 'icon-dashboard' }
        }
      })
      await renderWizard({ dashboardGeneralSettings: settings }, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()

      expect(onSave).toHaveBeenCalledOnce()
      const [_dashboardId, savedSettings] = onSave.mock.calls[0]!
      expect(savedSettings.menu.icon).toEqual({ name: 'icon-dashboard' })
    })

    it('includes emblem in icon when both icon and emblem are set', async () => {
      const onSave = vi.fn()
      const settings = makeGeneralSettings({
        menu: {
          topic: 'monitoring',
          sort_index: 10,
          is_show_more: false,
          search_terms: [],
          icon: { name: 'icon-dashboard', emblem: 'emblem-warning' }
        }
      })
      await renderWizard({ dashboardGeneralSettings: settings }, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()

      expect(onSave).toHaveBeenCalledOnce()
      const [_dashboardId, savedSettings] = onSave.mock.calls[0]!
      expect(savedSettings.menu.icon).toEqual({
        name: 'icon-dashboard',
        emblem: 'emblem-warning'
      })
    })

    it('does not set icon when dashboardIcon is null', async () => {
      const onSave = vi.fn()
      await renderWizard({}, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()

      expect(onSave).toHaveBeenCalledOnce()
      const [_dashboardId, savedSettings] = onSave.mock.calls[0]!
      expect(savedSettings.menu.icon).toBeUndefined()
    })
  })

  describe('Description update', () => {
    it('preserves the description in emitted settings', async () => {
      const onSave = vi.fn()
      const settings = makeGeneralSettings({ description: 'Some description' })
      await renderWizard({ dashboardGeneralSettings: settings }, { onSave })
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()

      expect(onSave).toHaveBeenCalledOnce()
      const [_dashboardId, savedSettings] = onSave.mock.calls[0]!
      expect(savedSettings.description).toBe('Some description')
    })
  })

  describe('Sort index zero', () => {
    it('emits "save" when sort index is zero (valid non-negative integer)', async () => {
      const onSave = vi.fn()
      await renderWizard(
        {
          dashboardGeneralSettings: makeGeneralSettings({
            menu: {
              topic: 'monitoring',
              sort_index: 0,
              is_show_more: false,
              search_terms: []
            }
          })
        },
        { onSave }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await flushPromises()
      expect(onSave).toHaveBeenCalledOnce()
    })
  })
})
