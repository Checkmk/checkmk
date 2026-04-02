/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import CloneDashboardWizard from '@/dashboard/components/Wizard/wizards/dashboard-clone/CloneDashboardWizard.vue'
import { DashboardLayout, DashboardOwnerType } from '@/dashboard/types/dashboard'

import { flushPromises, wrapInSuspense } from '../../utils.ts'

vi.mock(
  '@/dashboard/components/Wizard/components/DashboardSettings/VisibilityProperties.vue',
  () => ({
    default: { template: '<div data-testid="visibility-properties-stub" />' }
  })
)

vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/GeneralProperties.vue', () => ({
  default: { template: '<div data-testid="general-properties-stub" />' }
}))

vi.mock(
  '@/dashboard/components/Wizard/components/DashboardSettings/DashboardLayoutSelector.vue',
  () => ({
    default: {
      name: 'DashboardLayoutSelector',
      template: '<div data-testid="dashboard-layout-selector-stub" />'
    }
  })
)

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    listMainMenuTopics: vi.fn().mockResolvedValue([
      { id: 'monitoring', title: 'Monitoring', sortIndex: 1, isDefault: true },
      { id: 'other', title: 'Other', sortIndex: 2, isDefault: false }
    ]),
    listDashboardMetadata: vi.fn().mockResolvedValue([])
  }
}))

const mockValidateGeneralSettings = vi.hoisted(() => vi.fn().mockResolvedValue(true))
const mockBuildSettings = vi.hoisted(() =>
  vi.fn().mockReturnValue({
    title: { text: 'My Dashboard', render: true, include_context: false },
    menu: { topic: 'other', sort_index: 99, is_show_more: false, search_terms: [] },
    visibility: { hide_in_monitor_menu: true, hide_in_drop_down_menus: false, share: 'no' }
  })
)

vi.mock(
  '@/dashboard/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings',
  () => ({
    useDashboardGeneralSettings: vi.fn(() =>
      Promise.resolve({
        name: ref('My Dashboard'),
        nameErrors: ref([]),
        createUniqueId: ref(true),
        uniqueId: ref('my_dashboard'),
        uniqueIdErrors: ref([]),
        dashboardIcon: ref(null),
        dashboardEmblem: ref(null),
        showInMonitorMenu: ref(false),
        monitorMenuTopic: ref(''),
        sortIndex: ref(99),
        sortIndexError: ref([]),
        addFilterSuffix: ref(false),
        validateGeneralSettings: mockValidateGeneralSettings,
        buildSettings: mockBuildSettings
      })
    )
  })
)

const defaultGeneralSettings = {
  title: { text: 'My Dashboard', render: true, include_context: false },
  menu: { topic: 'monitoring', sort_index: 0, is_show_more: false, search_terms: [] },
  visibility: { hide_in_monitor_menu: false, hide_in_drop_down_menus: false, share: 'no' }
}

const defaultProps = {
  referenceDashboardId: 'my_dashboard',
  referenceDashboardGeneralSettings: { ...defaultGeneralSettings },
  referenceDashboardRestrictedToSingle: [] as string[],
  referenceDashboardLayoutType: DashboardLayout.RESPONSIVE_GRID,
  referenceDashboardType: DashboardOwnerType.BUILT_IN,
  availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
  loggedInUser: 'admin'
}

async function renderWizard(
  props: Partial<typeof defaultProps> = {},
  callbacks: {
    onCloneDashboard?: (...args: unknown[]) => void
    onCancelClone?: () => void
  } = {}
) {
  const mergedProps = { ...defaultProps, ...props, ...callbacks }
  render(wrapInSuspense(CloneDashboardWizard, { props: mergedProps }))
  await flushPromises()
}

describe('CloneDashboardWizard', () => {
  beforeEach(() => {
    mockValidateGeneralSettings.mockResolvedValue(true)
    mockBuildSettings.mockReturnValue({
      title: { text: 'My Dashboard', render: true, include_context: false },
      menu: { topic: 'other', sort_index: 99, is_show_more: false, search_terms: [] },
      visibility: { hide_in_monitor_menu: true, hide_in_drop_down_menus: false, share: 'no' }
    })

    // Catch output from Suspense component informing its unstable nature
    vi.spyOn(console, 'info').mockImplementation(() => {})
  })

  describe('Render', () => {
    it('should render the Clone dashboard title', async () => {
      await renderWizard()
      expect(await screen.findByText('Clone dashboard')).toBeInTheDocument()
    })

    it('should render the Clone button', async () => {
      await renderWizard()
      expect(await screen.findByRole('button', { name: 'Clone' })).toBeInTheDocument()
    })

    it('should render the Cancel button', async () => {
      await renderWizard()
      expect(await screen.findByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('should render the GeneralProperties component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('general-properties-stub')).toBeInTheDocument()
    })

    it('should render the VisibilityProperties component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('visibility-properties-stub')).toBeInTheDocument()
    })

    it('should render the DashboardLayoutSelector component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('dashboard-layout-selector-stub')).toBeInTheDocument()
    })

    it('should render the Dashboard type label', async () => {
      await renderWizard()
      expect(await screen.findByText('Dashboard type')).toBeInTheDocument()
    })
  })

  describe('Dashboard scope display', () => {
    it('should show "Unrestricted" when referenceDashboardRestrictedToSingle is empty', async () => {
      await renderWizard({ referenceDashboardRestrictedToSingle: [] })
      expect(await screen.findByText('Unrestricted')).toBeInTheDocument()
    })

    it('should show the single info value when referenceDashboardRestrictedToSingle has one entry', async () => {
      await renderWizard({ referenceDashboardRestrictedToSingle: ['host'] })
      expect(await screen.findByText('host')).toBeInTheDocument()
    })

    it('should show comma-joined values when referenceDashboardRestrictedToSingle has multiple entries', async () => {
      await renderWizard({ referenceDashboardRestrictedToSingle: ['host', 'service'] })
      expect(await screen.findByText('host, service')).toBeInTheDocument()
    })
  })

  describe('cancel-clone event', () => {
    it('should emit "cancel-clone" when the Cancel button is clicked', async () => {
      const onCancelClone = vi.fn()
      await renderWizard({}, { onCancelClone })
      await fireEvent.click(screen.getByRole('button', { name: /Cancel/i }))
      expect(onCancelClone).toHaveBeenCalledOnce()
    })

    it('should emit "cancel-clone" when the back button in the header is clicked', async () => {
      const onCancelClone = vi.fn()
      await renderWizard({}, { onCancelClone })
      await fireEvent.click(screen.getByTestId('back-button'))
      expect(onCancelClone).toHaveBeenCalledOnce()
    })
  })

  describe('clone-dashboard event', () => {
    it('should emit "clone-dashboard" with correct payload when Clone is clicked with valid data', async () => {
      const onCloneDashboard = vi.fn()
      await renderWizard({}, { onCloneDashboard })
      await fireEvent.click(screen.getByRole('button', { name: 'Clone' }))
      await flushPromises()

      expect(onCloneDashboard).toHaveBeenCalledOnce()
      const [dashboardId, settings, layout] = onCloneDashboard.mock.calls[0]!
      expect(dashboardId).toBe('my_dashboard')
      expect(settings).toBeDefined()
      expect(layout).toBe(DashboardLayout.RESPONSIVE_GRID)
    })

    it('should not emit "clone-dashboard" when general settings validation fails', async () => {
      mockValidateGeneralSettings.mockResolvedValue(false)
      const onCloneDashboard = vi.fn()
      await renderWizard({}, { onCloneDashboard })
      await fireEvent.click(screen.getByRole('button', { name: 'Clone' }))
      await flushPromises()

      expect(onCloneDashboard).not.toHaveBeenCalled()
    })
  })

  describe('Dashboard naming based on owner type', () => {
    it('should call useDashboardGeneralSettings with original id for BUILT_IN dashboards', async () => {
      const { useDashboardGeneralSettings } = await import(
        '@/dashboard/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings'
      )
      await renderWizard({
        referenceDashboardId: 'built_in_dash',
        referenceDashboardType: DashboardOwnerType.BUILT_IN
      })
      expect(useDashboardGeneralSettings).toHaveBeenCalledWith(
        'admin',
        expect.objectContaining({ title: expect.objectContaining({ text: 'My Dashboard' }) }),
        'built_in_dash',
        false
      )
    })

    it('should call useDashboardGeneralSettings with _clone suffix id for CUSTOM dashboards', async () => {
      const { useDashboardGeneralSettings } = await import(
        '@/dashboard/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings'
      )
      await renderWizard({
        referenceDashboardId: 'custom_dash',
        referenceDashboardType: DashboardOwnerType.CUSTOM
      })
      expect(useDashboardGeneralSettings).toHaveBeenCalledWith(
        'admin',
        expect.objectContaining({ title: expect.objectContaining({ text: 'My Dashboard_clone' }) }),
        'custom_dash_clone',
        true
      )
    })
  })

  describe('Layout handling', () => {
    it('should use RELATIVE_GRID layout when reference is RELATIVE_GRID', async () => {
      const onCloneDashboard = vi.fn()
      await renderWizard(
        { referenceDashboardLayoutType: DashboardLayout.RELATIVE_GRID },
        { onCloneDashboard }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Clone' }))
      await flushPromises()

      const [, , layout] = onCloneDashboard.mock.calls[0]!
      expect(layout).toBe(DashboardLayout.RELATIVE_GRID)
    })

    it('should use RESPONSIVE_GRID layout when reference is RESPONSIVE_GRID', async () => {
      const onCloneDashboard = vi.fn()
      await renderWizard(
        { referenceDashboardLayoutType: DashboardLayout.RESPONSIVE_GRID },
        { onCloneDashboard }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Clone' }))
      await flushPromises()

      const [, , layout] = onCloneDashboard.mock.calls[0]!
      expect(layout).toBe(DashboardLayout.RESPONSIVE_GRID)
    })
  })
})
