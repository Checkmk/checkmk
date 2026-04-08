/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import GeneralSettings from '@/dashboard/components/Wizard/wizards/dashboard-settings/components/GeneralSettings.vue'

// Stub GeneralProperties to avoid its async/complex internals
// They have their own dedicated tests, so mocking should be okay.
vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/GeneralProperties.vue', () => ({
  default: {
    name: 'GeneralProperties',
    template: '<div data-testid="general-properties-stub" />'
  }
}))

const defaultProps = {
  name: 'My Dashboard',
  description: 'A description',
  addFilterSuffix: false,
  createUniqueId: false,
  uniqueId: 'my_dashboard',
  dashboardIcon: null,
  dashboardEmblem: null,
  nameValidationErrors: [],
  uniqueIdValidationErrors: [],
  dashboardType: 'Unrestricted',
  originalDashboardId: 'my_dashboard',
  loggedInUser: 'admin'
}

function renderGeneralSettings(overrides: Record<string, unknown> = {}) {
  return render(GeneralSettings, { props: { ...defaultProps, ...overrides } })
}

describe('GeneralSettings', () => {
  it('renders the dashboard type', () => {
    renderGeneralSettings()
    expect(screen.getByText('Dashboard type')).toBeInTheDocument()
    expect(screen.getByText('Unrestricted')).toBeInTheDocument()
  })

  it('displays a joined restricted type', () => {
    renderGeneralSettings({ dashboardType: 'host, service' })
    expect(screen.getByText('host, service')).toBeInTheDocument()
  })

  it('renders the GeneralProperties stub', () => {
    renderGeneralSettings()
    expect(screen.getByTestId('general-properties-stub')).toBeInTheDocument()
  })

  it('renders the description input with the provided value', () => {
    renderGeneralSettings({ description: 'My custom description' })
    const input = screen.getByPlaceholderText('Enter description') as HTMLInputElement
    expect(input.value).toBe('My custom description')
  })

  it('renders an empty description input when description is empty', () => {
    renderGeneralSettings({ description: '' })
    const input = screen.getByPlaceholderText('Enter description') as HTMLInputElement
    expect(input.value).toBe('')
  })
})
