/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types.ts'
import { kioskMode } from 'cmk-ui-library/lib/kiosk'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardMenuHeader from '@/dashboard/components/DashboardMenuHeader/DashboardMenuHeader.vue'
import type { SelectedDashboard } from '@/dashboard/components/DashboardMenuHeader/types'
import type { DashboardMetadata, DashboardTokenModel } from '@/dashboard/types/dashboard'
import { DashboardOwnerType } from '@/dashboard/types/dashboard'
import { copyToClipboard, dashboardAPI } from '@/dashboard/utils.ts'

const TZ = 'Europe/Berlin'

const testRange: DateTimeRange = (() => {
  const to: ZonedDateTime = toZoned(new CalendarDateTime(2026, 3, 10, 12, 0), TZ, 'compatible')
  return { from: to.subtract({ hours: 4 }), to }
})()

const testGlobalTimePicker: GlobalTimePickerProps = {
  custom_time_ranges: [{ title: 'Last 1 hour', total_seconds: 3600 }],
  default_time_range: 4 * 3600,
  server_time_zone: TZ,
  first_day_of_week: null,
  refresh: { interval_seconds: null, starts_live: false, reloads_page_content: false }
}

vi.mock('@/dashboard/utils.ts', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(undefined),
  dashboardAPI: {
    listDashboardMetadata: vi.fn().mockResolvedValue([])
  },
  urlHandler: {
    getDashboardUrl: vi.fn().mockReturnValue(new URL('http://localhost/dashboard.py'))
  }
}))

const customDashboard: SelectedDashboard = {
  name: 'my-dashboard',
  owner: 'admin',
  title: 'My Dashboard',
  type: DashboardOwnerType.CUSTOM
}

const builtInDashboard: SelectedDashboard = {
  name: 'main',
  owner: '',
  title: 'Main Dashboard',
  type: DashboardOwnerType.BUILT_IN
}

const activeToken: DashboardTokenModel = {
  token_id: 'tok',
  is_disabled: false,
  expires_at: null,
  comment: '',
  issued_at: '2025-01-01T00:00:00Z'
}

interface RenderProps {
  selectedDashboard?: SelectedDashboard | null
  canEditDashboard?: boolean
  linkUserGuide?: string
  isEditMode?: boolean
  publicToken?: DashboardTokenModel | null
  isEmptyDashboard?: boolean
  isDashboardLoading?: boolean
  runtimeFilters?: Record<string, string>
  globalTimePicker?: GlobalTimePickerProps
  range?: DateTimeRange
}

function renderHeader(props: RenderProps = {}) {
  return render(DashboardMenuHeader, {
    props: {
      selectedDashboard: customDashboard,
      canEditDashboard: true,
      linkUserGuide: 'https://docs.checkmk.com',
      isEditMode: false,
      publicToken: null,
      isEmptyDashboard: false,
      isDashboardLoading: false,
      runtimeFilters: {},
      globalTimePicker: testGlobalTimePicker,
      range: testRange,
      'onUpdate:range': () => {},
      ...props
    }
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DashboardMenuHeader', () => {
  describe('view mode rendering', () => {
    it('renders the Dashboard label', () => {
      renderHeader()
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })

    it('renders the Filter button in view mode', () => {
      renderHeader()
      expect(screen.getByRole('button', { name: 'Filter' })).toBeInTheDocument()
    })

    it('does not render Filter button in edit mode', () => {
      renderHeader({ isEditMode: true })
      expect(screen.queryByRole('button', { name: 'Filter' })).not.toBeInTheDocument()
    })

    it('shows "Edit widgets" for custom editable dashboard', () => {
      renderHeader({ canEditDashboard: true, isEmptyDashboard: false })
      expect(screen.getByText('Edit widgets')).toBeInTheDocument()
    })

    it('shows "Add widget" for empty editable dashboard', () => {
      renderHeader({ canEditDashboard: true, isEmptyDashboard: true })
      expect(screen.getByText('Add widget')).toBeInTheDocument()
    })

    it('shows "Clone" button for built-in dashboard', () => {
      renderHeader({ selectedDashboard: builtInDashboard })
      expect(screen.getByText('Clone')).toBeInTheDocument()
    })

    it('does not show "Clone" button for custom dashboard', () => {
      renderHeader({ selectedDashboard: customDashboard })
      expect(screen.queryByText('Clone')).not.toBeInTheDocument()
    })

    it('renders Share and Settings dropdowns in view mode', () => {
      renderHeader()
      expect(screen.getByText('Share')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })
  })

  describe('page navigation toggle', () => {
    afterEach(() => {
      vi.restoreAllMocks()
    })

    async function openNavigationToggle(): Promise<HTMLAnchorElement> {
      renderHeader()
      await fireEvent.click(screen.getByText('Settings'))
      return screen.getByText('Show page navigation').closest('a') as HTMLAnchorElement
    }

    it('shows the toggle as on and links to kiosk mode when the navigation is visible', async () => {
      vi.spyOn(kioskMode, 'isActive').mockReturnValue(false)
      const link = await openNavigationToggle()
      expect(new URL(link.href).searchParams.get('kiosk')).toBe('true')
      expect(link.querySelector('img')!.src).toContain('icon_toggle_on.svg')
    })

    it('shows the toggle as off and links out of kiosk mode when the navigation is hidden', async () => {
      vi.spyOn(kioskMode, 'isActive').mockReturnValue(true)
      const link = await openNavigationToggle()
      expect(new URL(link.href).searchParams.has('kiosk')).toBe(false)
      expect(link.querySelector('img')!.src).toContain('icon_toggle_off.svg')
    })
  })

  describe('edit mode rendering', () => {
    it('renders Save, Cancel, and Add widget buttons in edit mode', () => {
      renderHeader({ isEditMode: true })
      expect(screen.getByText('Save')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Add widget')).toBeInTheDocument()
    })

    it('does not render Share or Settings dropdowns in edit mode', () => {
      renderHeader({ isEditMode: true })
      expect(screen.queryByText('Share')).not.toBeInTheDocument()
      expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    })
  })

  describe('emits', () => {
    it('emits open-runtime-filter when Filter button is clicked', async () => {
      const { emitted } = renderHeader()
      await fireEvent.click(screen.getByRole('button', { name: 'Filter' }))
      expect(emitted()['open-runtime-filter']).toHaveLength(1)
    })

    it('emits enter-edit when Edit widgets is clicked', async () => {
      const { emitted } = renderHeader()
      await fireEvent.click(screen.getByText('Edit widgets'))
      expect(emitted()['enter-edit']).toHaveLength(1)
    })

    it('emits open-widget-workflow when Add widget is clicked on empty dashboard', async () => {
      const { emitted } = renderHeader({ isEmptyDashboard: true })
      await fireEvent.click(screen.getByText('Add widget'))
      expect(emitted()['open-widget-workflow']).toHaveLength(1)
    })

    it('emits save when Save is clicked in edit mode', async () => {
      const { emitted } = renderHeader({ isEditMode: true })
      await fireEvent.click(screen.getByText('Save'))
      expect(emitted()['save']).toHaveLength(1)
    })

    it('emits cancel-edit when Cancel is clicked in edit mode', async () => {
      const { emitted } = renderHeader({ isEditMode: true })
      await fireEvent.click(screen.getByText('Cancel'))
      expect(emitted()['cancel-edit']).toHaveLength(1)
    })

    it('emits open-widget-workflow when Add widget is clicked in edit mode', async () => {
      const { emitted } = renderHeader({ isEditMode: true })
      await fireEvent.click(screen.getByText('Add widget'))
      expect(emitted()['open-widget-workflow']).toHaveLength(1)
    })

    it('emits open-clone-workflow when Clone is clicked for built-in dashboard', async () => {
      const { emitted } = renderHeader({ selectedDashboard: builtInDashboard })
      await fireEvent.click(screen.getByText('Clone'))
      expect(emitted()['open-clone-workflow']).toHaveLength(1)
    })

    it('emits set-dashboard when a dashboard is selected from DashboardSelector', async () => {
      vi.mocked(dashboardAPI.listDashboardMetadata).mockResolvedValueOnce([
        {
          name: 'test-dashboard',
          owner: 'admin',
          is_built_in: false,
          display: { title: 'Test Dashboard', hide_in_drop_down_menus: false, sort_index: 0 }
        }
      ] as DashboardMetadata[])

      const { emitted } = renderHeader()
      await fireEvent.focus(screen.getByRole('textbox'))

      await waitFor(() => {
        expect(screen.getByText('Test Dashboard')).toBeInTheDocument()
      })

      await fireEvent.click(screen.getByText('Test Dashboard'))
      expect(emitted()['set-dashboard']).toMatchObject([
        [expect.objectContaining({ name: 'test-dashboard' })]
      ])
    })

    it('calls copyToClipboard when "Copy internal link" is clicked', async () => {
      renderHeader()
      await fireEvent.click(screen.getByText('Share'))
      await waitFor(() => {
        expect(screen.getByText('Copy internal link')).toBeInTheDocument()
      })
      await fireEvent.click(screen.getByText('Copy internal link'))
      expect(copyToClipboard).toHaveBeenCalledOnce()
    })
  })

  describe('sharing status', () => {
    it('shows SharingStatus for editable custom dashboard', () => {
      renderHeader({
        canEditDashboard: true,
        selectedDashboard: customDashboard,
        publicToken: activeToken
      })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('active')).toBeInTheDocument()
    })

    it('shows paused SharingStatus when token is disabled', () => {
      renderHeader({
        canEditDashboard: true,
        selectedDashboard: customDashboard,
        publicToken: { ...activeToken, is_disabled: true }
      })
      expect(screen.getByText('Sharing')).toBeInTheDocument()
      expect(screen.getByText('paused')).toBeInTheDocument()
    })

    it('does not show SharingStatus for built-in dashboard', () => {
      renderHeader({
        canEditDashboard: true,
        selectedDashboard: builtInDashboard,
        publicToken: activeToken
      })
      expect(screen.queryByText('active')).not.toBeInTheDocument()
    })

    it('does not show SharingStatus when user cannot edit', () => {
      renderHeader({
        canEditDashboard: false,
        publicToken: activeToken
      })
      expect(screen.queryByText('active')).not.toBeInTheDocument()
    })
  })

  describe('disabled state', () => {
    it('disables Filter button when dashboard is loading', () => {
      renderHeader({ isDashboardLoading: true })
      const filterButton = screen.getByRole('button', { name: 'Filter' })
      expect(filterButton).toBeDisabled()
    })

    it('disables Filter button when no dashboard is selected', () => {
      renderHeader({ selectedDashboard: null })
      const filterButton = screen.getByRole('button', { name: 'Filter' })
      expect(filterButton).toBeDisabled()
    })
  })
})
