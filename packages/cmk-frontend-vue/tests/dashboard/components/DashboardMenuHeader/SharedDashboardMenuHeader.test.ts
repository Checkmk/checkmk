/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import SharedDashboardMenuHeader from '@/dashboard/components/DashboardMenuHeader/SharedDashboardMenuHeader.vue'

function renderSharedHeader(props: { dashboardTitle: string }) {
  return render(SharedDashboardMenuHeader, { props })
}

describe('SharedDashboardMenuHeader', () => {
  describe('rendering', () => {
    it('renders the dashboard title', () => {
      renderSharedHeader({ dashboardTitle: 'My Shared Dashboard' })
      expect(screen.getByText('My Shared Dashboard')).toBeInTheDocument()
    })

    it('renders UTC date and time elements', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const dateEl = document.querySelector('.db-shared-dashboard-menu-header__utc-date')
      const timeEl = document.querySelector('.db-shared-dashboard-menu-header__utc-time-only')
      expect(dateEl).not.toBeNull()
      await waitFor(() => {
        expect(dateEl!.textContent).toMatch(/^\d{2}-\d{2}-\d{4}$/)
      })
      expect(timeEl).not.toBeNull()
      expect(timeEl!.textContent).toContain('UTC')
    })
  })

  describe('settings menu', () => {
    it('does not show menu by default', () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      expect(screen.queryByText('Show date and time')).not.toBeInTheDocument()
    })

    it('opens settings menu when menu button is clicked', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const menuButton = screen.getByLabelText('Settings Menu')
      await fireEvent.click(menuButton)
      expect(screen.getByText('Show date and time')).toBeInTheDocument()
    })

    it('closes settings menu when menu button is clicked again', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const menuButton = screen.getByLabelText('Settings Menu')
      await fireEvent.click(menuButton)
      expect(screen.getByText('Show date and time')).toBeInTheDocument()
      await fireEvent.click(menuButton)
      expect(screen.queryByText('Show date and time')).not.toBeInTheDocument()
    })

    it('sets aria-expanded correctly on menu toggle', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const menuButton = screen.getByLabelText('Settings Menu')
      expect(menuButton).toHaveAttribute('aria-expanded', 'false')
      await fireEvent.click(menuButton)
      expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    })
  })

  describe('date/time toggle', () => {
    it('hides date/time section when toggle is clicked', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      expect(document.querySelector('.db-shared-dashboard-menu-header__utc-time')).not.toBeNull()

      await fireEvent.click(screen.getByLabelText('Settings Menu'))
      await fireEvent.click(screen.getByText('Show date and time'))

      expect(document.querySelector('.db-shared-dashboard-menu-header__utc-time')).toBeNull()
    })

    it('shows date/time again when toggle is clicked twice', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })

      await fireEvent.click(screen.getByLabelText('Settings Menu'))
      await fireEvent.click(screen.getByText('Show date and time'))
      expect(document.querySelector('.db-shared-dashboard-menu-header__utc-time')).toBeNull()

      await fireEvent.click(screen.getByLabelText('Settings Menu'))
      await fireEvent.click(screen.getByText('Show date and time'))
      expect(document.querySelector('.db-shared-dashboard-menu-header__utc-time')).not.toBeNull()
    })
  })
})
