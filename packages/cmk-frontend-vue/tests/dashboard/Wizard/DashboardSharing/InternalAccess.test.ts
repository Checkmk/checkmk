/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import InternalAccess from '@/dashboard/components/Wizard/wizards/dashboard-sharing/InternalAccess.vue'

const DASHBOARD_URL = 'https://example.checkmk.com/dashboard.py?name=my-dash'

describe('InternalAccess', () => {
  describe('Rendering', () => {
    it('renders static text', () => {
      render(InternalAccess, { props: { dashboardUrl: DASHBOARD_URL } })
      expect(screen.getByText('Internal access')).toBeInTheDocument()
      expect(
        screen.getByText('Users with access permissions can view this dashboard')
      ).toBeInTheDocument()
      expect(screen.getByText('Dashboard URL')).toBeInTheDocument()
    })

    it('renders the dashboard URL', () => {
      render(InternalAccess, { props: { dashboardUrl: DASHBOARD_URL } })
      expect(screen.getByText(DASHBOARD_URL)).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('copies the dashboard URL to clipboard when the copy button is clicked', async () => {
      const user = userEvent.setup()
      render(InternalAccess, { props: { dashboardUrl: DASHBOARD_URL } })

      await user.click(screen.getByTestId('copy-internal-url'))

      expect(await navigator.clipboard.readText()).toBe(DASHBOARD_URL)
    })
  })
})
