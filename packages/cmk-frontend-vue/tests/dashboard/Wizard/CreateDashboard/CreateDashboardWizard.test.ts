/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type PropType, nextTick, ref } from 'vue'

import CreateDashboardWizard from '@/dashboard/components/Wizard/wizards/create-dashboard/CreateDashboardWizard.vue'
import { DashboardLayout } from '@/dashboard/types/dashboard'

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
  '@/dashboard/components/Wizard/wizards/create-dashboard/components/DashboardTypeSelector.vue',
  () => ({
    default: {
      name: 'DashboardTypeSelector',
      props: { dashboardType: { type: String, required: true } },
      emits: ['update:dashboardType'],
      template: `<div data-testid="dashboard-type-selector-stub">
        <button data-testid="type-unrestricted" @click="$emit('update:dashboardType', 'UNRESTRICTED')">unrestricted</button>
        <button data-testid="type-specific-host" @click="$emit('update:dashboardType', 'SPECIFIC_HOST')">specific_host</button>
        <button data-testid="type-custom" @click="$emit('update:dashboardType', 'CUSTOM')">custom</button>
      </div>`
    }
  })
)

vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/DashboardScope.vue', () => ({
  default: {
    name: 'DashboardScope',
    props: {
      selectedIds: { type: Array as PropType<string[]>, default: () => [] },
      selectionErrors: { type: Array as PropType<string[]>, default: () => [] }
    },
    emits: ['update:selectedIds'],
    template: `<div data-testid="dashboard-scope">
        <button data-testid="add-scope" @click="$emit('update:selectedIds', ['some_scope'])">add scope</button>
      </div>`
  }
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

const defaultProps = {
  availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
  loggedInUser: 'admin'
}

async function renderWizard(
  props: Partial<typeof defaultProps> = {},
  callbacks: {
    onCreateDashboard?: (...args: unknown[]) => void
    onCancelCreation?: () => void
  } = {}
) {
  const mergedProps = { ...defaultProps, ...props, ...callbacks }

  render(wrapInSuspense(CreateDashboardWizard, { props: mergedProps }))
  await flushPromises()
}

describe('CreateDashboard', () => {
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
    it('should render the Create dashboard title', async () => {
      await renderWizard()
      expect(await screen.findByText('Create dashboard')).toBeInTheDocument()
    })

    it('should render Create button', async () => {
      await renderWizard()
      expect(await screen.findByRole('button', { name: 'Create' })).toBeInTheDocument()
    })

    it('should render the Cancel button', async () => {
      await renderWizard()
      expect(await screen.findByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('should render the DashboardTypeSelector component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('dashboard-type-selector-stub')).toBeInTheDocument()
    })

    it('should render the GeneralProperties component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('general-properties-stub')).toBeInTheDocument()
    })

    it('should render the VisibilityProperties component', async () => {
      await renderWizard()
      expect(await screen.findByTestId('visibility-properties-stub')).toBeInTheDocument()
    })

    it('renders the DashboardLayoutSelector section', async () => {
      await renderWizard()
      expect(screen.getByTestId('dashboard-layout-selector-stub')).toBeInTheDocument()
    })
  })

  describe('Dashboard scope visibility', () => {
    it('should not show DashboardScope when type is UNRESTRICTED (default)', async () => {
      await renderWizard()
      expect(screen.queryByTestId('dashboard-scope')).not.toBeInTheDocument()
    })

    it('should not show DashboardScope when type is SPECIFIC_HOST', async () => {
      await renderWizard()
      await fireEvent.click(screen.getByTestId('type-specific-host'))
      await nextTick()
      expect(screen.queryByTestId('dashboard-scope')).not.toBeInTheDocument()
    })

    it('should show DashboardScope when type is CUSTOM', async () => {
      await renderWizard()
      await fireEvent.click(screen.getByTestId('type-custom'))
      await nextTick()
      expect(screen.getByTestId('dashboard-scope')).toBeInTheDocument()
    })

    it('should hide DashboardScope again when switching back from CUSTOM to UNRESTRICTED', async () => {
      await renderWizard()
      await fireEvent.click(screen.getByTestId('type-custom'))
      await nextTick()
      await fireEvent.click(screen.getByTestId('type-unrestricted'))
      await nextTick()
      expect(screen.queryByTestId('dashboard-scope')).not.toBeInTheDocument()
    })
  })

  describe('cancel-creation event', () => {
    it('should emit "cancel-creation" when the Cancel button is clicked', async () => {
      const onCancelCreation = vi.fn()
      await renderWizard({}, { onCancelCreation })
      await fireEvent.click(screen.getByRole('button', { name: /Cancel/i }))
      expect(onCancelCreation).toHaveBeenCalledOnce()
    })

    it('should emit "cancel-creation" when the close button in the header is clicked', async () => {
      const onCancelCreation = vi.fn()
      await renderWizard({}, { onCancelCreation })
      await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
      expect(onCancelCreation).toHaveBeenCalledOnce()
    })
  })

  describe('create-dashboard event', () => {
    it('should emit "create-dashboard" with correct payload when Create is clicked with valid data', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })
      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      expect(onCreateDashboard).toHaveBeenCalledOnce()
      const [dashboardId, settings, layout, scopeIds] = onCreateDashboard.mock.calls[0]!
      expect(dashboardId).toBe('my_dashboard')
      expect(settings).toBeDefined()
      expect(layout).toBe(DashboardLayout.RESPONSIVE_GRID)
      expect(scopeIds).toEqual([])
    })

    it('should not emit "create-dashboard" when general settings validation fails', async () => {
      mockValidateGeneralSettings.mockResolvedValue(false)
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })
      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      expect(onCreateDashboard).not.toHaveBeenCalled()
    })

    it('should not emit "create-dashboard" when CUSTOM type has no scope selected', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })

      await fireEvent.click(screen.getByTestId('type-custom'))
      await nextTick()

      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      expect(onCreateDashboard).not.toHaveBeenCalled()
    })
  })

  describe('Layout default', () => {
    it('should default to RESPONSIVE_GRID when it is in availableLayouts', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard(
        { availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID] },
        { onCreateDashboard }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , layout] = onCreateDashboard.mock.calls[0]!
      expect(layout).toBe(DashboardLayout.RESPONSIVE_GRID)
    })

    it('should fall back to RELATIVE_GRID when RESPONSIVE_GRID is not available', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard(
        { availableLayouts: [DashboardLayout.RELATIVE_GRID] },
        { onCreateDashboard }
      )
      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , layout] = onCreateDashboard.mock.calls[0]!
      expect(layout).toBe(DashboardLayout.RELATIVE_GRID)
    })
  })

  describe('Scope handling on create', () => {
    it('should emit scopeIds as ["host"] when type is SPECIFIC_HOST', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })

      await fireEvent.click(screen.getByTestId('type-specific-host'))
      await nextTick()

      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , , scopeIds] = onCreateDashboard.mock.calls[0]!
      expect(scopeIds).toEqual(['host'])
    })

    it('should emit empty scopeIds when type is UNRESTRICTED', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })
      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , , scopeIds] = onCreateDashboard.mock.calls[0]!
      expect(scopeIds).toEqual([])
    })

    it('should emit selected scopeIds when type is CUSTOM and scope is selected', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })

      await fireEvent.click(screen.getByTestId('type-custom'))
      await nextTick()
      await fireEvent.click(screen.getByTestId('add-scope'))
      await nextTick()

      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , , scopeIds] = onCreateDashboard.mock.calls[0]!
      expect(scopeIds).toEqual(['some_scope'])
    })

    it('should emit ["host"] for SPECIFIC_HOST even if scopeIds were previously set by CUSTOM', async () => {
      const onCreateDashboard = vi.fn()
      await renderWizard({}, { onCreateDashboard })

      // Set CUSTOM type and add a scope
      await fireEvent.click(screen.getByTestId('type-custom'))
      await nextTick()
      await fireEvent.click(screen.getByTestId('add-scope'))
      await nextTick()

      // Switch to SPECIFIC_HOST — _selectSingleInfo should override to ['host']
      await fireEvent.click(screen.getByTestId('type-specific-host'))
      await nextTick()

      await fireEvent.click(screen.getByRole('button', { name: 'Create' }))
      await flushPromises()

      const [, , , scopeIds] = onCreateDashboard.mock.calls[0]!
      expect(scopeIds).toEqual(['host'])
    })
  })
})
