/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardLayoutSelector from '@/dashboard/components/Wizard/components/DashboardSettings/DashboardLayoutSelector.vue'
import { DashboardLayout } from '@/dashboard/types/dashboard'

describe('DashboardLayoutSelector', () => {
  describe('Rendering', () => {
    it('renders both radio buttons when both layouts are available', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      expect(screen.getByLabelText('Responsive')).toBeInTheDocument()
      expect(screen.getByLabelText('Anchored')).toBeInTheDocument()
    })

    it('renders only the Responsive radio when only RESPONSIVE_GRID is available', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      expect(screen.getByLabelText('Responsive')).toBeInTheDocument()
      expect(screen.queryByLabelText('Anchored')).not.toBeInTheDocument()
    })

    it('renders only the Anchored radio when only RELATIVE_GRID is available', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RELATIVE_GRID
        }
      })
      expect(screen.getByLabelText('Anchored')).toBeInTheDocument()
      expect(screen.queryByLabelText('Responsive')).not.toBeInTheDocument()
    })

    it('renders no radio buttons when availableLayouts is empty', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      expect(screen.queryByLabelText('Responsive')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Anchored')).not.toBeInTheDocument()
    })

    it('renders the "Dashboard layout" field description', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      expect(screen.getByText('Dashboard layout')).toBeInTheDocument()
    })

    it('checks the Responsive radio when dashboardLayout is RESPONSIVE_GRID', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      expect(screen.getByLabelText('Responsive')).toBeChecked()
      expect(screen.getByLabelText('Anchored')).not.toBeChecked()
    })

    it('checks the Anchored radio when dashboardLayout is RELATIVE_GRID', () => {
      render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RELATIVE_GRID
        }
      })
      expect(screen.getByLabelText('Anchored')).toBeChecked()
      expect(screen.getByLabelText('Responsive')).not.toBeChecked()
    })
  })

  describe('Events', () => {
    it('emits update:dashboardLayout with RELATIVE_GRID when Anchored radio is clicked', async () => {
      const { emitted } = render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      await fireEvent.click(screen.getByLabelText('Anchored'))
      expect(emitted()['update:dashboardLayout']).toEqual([[DashboardLayout.RELATIVE_GRID]])
    })

    it('emits update:dashboardLayout with RESPONSIVE_GRID when Responsive radio is clicked', async () => {
      const { emitted } = render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RELATIVE_GRID
        }
      })
      await fireEvent.click(screen.getByLabelText('Responsive'))
      expect(emitted()['update:dashboardLayout']).toEqual([[DashboardLayout.RESPONSIVE_GRID]])
    })

    it('emits exactly one event per click', async () => {
      const { emitted } = render(DashboardLayoutSelector, {
        props: {
          availableLayouts: [DashboardLayout.RESPONSIVE_GRID, DashboardLayout.RELATIVE_GRID],
          dashboardLayout: DashboardLayout.RESPONSIVE_GRID
        }
      })
      await fireEvent.click(screen.getByLabelText('Anchored'))
      expect(emitted()['update:dashboardLayout']).toHaveLength(1)
    })
  })
})
