/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen } from '@testing-library/vue'
import type { CreateRelay } from 'cmk-shared-typing/typescript/create_relay'

import ModeCreateRelayApp from '@/mode-relay/ModeCreateRelayApp.vue'

const mockProps: CreateRelay = {
  alias_validation: {
    regex: '^[a-zA-Z0-9_-]+$',
    regex_help: 'Alias must contain only letters, numbers, underscores, and hyphens'
  },
  urls: {
    create_host: '/wato.py?mode=newhost',
    relay_overview: '/wato.py?mode=relay_overview',
    documentation: 'https://docs.checkmk.com/relay'
  },
  site_name: 'test_site',
  domain: 'localhost',
  agent_receiver_port: 8000,
  site_version: '2.5.0',
  supported_os: ['Ubuntu 24.04 LTS', 'Red Hat Enterprise Linux (RHEL) 10']
}

afterEach(cleanup)

describe('ModeCreateRelayApp', () => {
  test('Linux path renders all 5 step headings in order', () => {
    render(ModeCreateRelayApp, { props: mockProps })

    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent?.trim())

    expect(headings).toEqual([
      'Download the Relay installation script',
      'Name the relay',
      'Install Podman',
      'Run the installation script',
      'Registration results'
    ])
  })

  test('Windows path renders all 5 step headings in order', async () => {
    render(ModeCreateRelayApp, { props: { ...mockProps, exp_add_windows_relay_enabled: true } })

    await userEvent.click(screen.getByText('Windows'))

    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent?.trim())

    expect(headings).toEqual([
      'Install WSL2',
      'Download the MSI installer',
      'Name the relay',
      'Run the MSI installer',
      'Registration results'
    ])
  })

  test('switching OS resets wizard to step 1', async () => {
    render(ModeCreateRelayApp, { props: { ...mockProps, exp_add_windows_relay_enabled: true } })

    // Switch to Windows — WSL2 is step 1, its content should be visible
    await userEvent.click(screen.getByText('Windows'))
    expect(screen.getByTestId('install-wsl2-command')).toBeVisible()

    // Switch back to Linux — InstallRelay is step 1, its content should be visible
    await userEvent.click(screen.getByText('Linux'))
    expect(screen.getByLabelText('Download relay install script command')).toBeVisible()
  })

  test('OS toggle is hidden when exp_add_windows_relay_enabled is false', () => {
    render(ModeCreateRelayApp, {
      props: { ...mockProps, exp_add_windows_relay_enabled: false }
    })

    expect(screen.queryByText('Linux')).not.toBeInTheDocument()
    expect(screen.queryByText('Windows')).not.toBeInTheDocument()
  })

  test('OS toggle is hidden when exp_add_windows_relay_enabled is not set', () => {
    render(ModeCreateRelayApp, { props: mockProps })

    expect(screen.queryByText('Linux')).not.toBeInTheDocument()
    expect(screen.queryByText('Windows')).not.toBeInTheDocument()
  })
})
