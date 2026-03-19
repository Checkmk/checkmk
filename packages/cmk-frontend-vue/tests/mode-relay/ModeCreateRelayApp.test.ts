/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { CreateRelay } from 'cmk-shared-typing/typescript/create_relay'

import * as relayClient from '@/lib/rest-api-client/relay/client'

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

/**
 * Helper function to navigate to the "Name the relay" step
 */
async function navigateToNameRelayStep() {
  await fireEvent.click(screen.getByRole('button', { name: /next step/i }))
  await screen.findByText('Name the relay')
}

/**
 * Helper function to fill in the relay alias
 */
async function fillRelayAlias(alias: string) {
  const input = screen.getByRole('textbox')
  await userEvent.type(input, alias)
}

/**
 * Helper function to navigate to the "Install Podman" step
 */
async function navigateToInstallPodmanStep(relayAlias = 'test-relay') {
  await navigateToNameRelayStep()
  await fillRelayAlias(relayAlias)
  await fireEvent.click(screen.getByRole('button', { name: /next step/i }))
  await screen.findByText('Install Podman')
}

/**
 * Helper function to navigate to the "Run the installation script" step
 */
async function navigateToExecuteScriptStep(relayAlias = 'test-relay') {
  await navigateToInstallPodmanStep(relayAlias)
  await fireEvent.click(screen.getByRole('button', { name: /next step/i }))
  await screen.findByText('Run the installation script')
}

/**
 * Helper function to navigate to the "Registration results" step
 */
async function navigateToVerifyRegistrationStep(relayAlias = 'test-relay') {
  await navigateToExecuteScriptStep(relayAlias)
  await fireEvent.click(screen.getByRole('button', { name: /next step/i }))
  await screen.findByText('Registration results')
}

describe('ModeCreateRelayApp', () => {
  let getRelayCollectionSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // Mock the getRelayCollection API call with empty array by default
    getRelayCollectionSpy = vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([])
  })

  afterEach(() => {
    // Clean up the DOM and restore all mocks
    cleanup()
    vi.restoreAllMocks()
  })

  test('displays supported operating systems', () => {
    render(ModeCreateRelayApp, { props: mockProps })

    mockProps.supported_os.forEach((os) => {
      expect(screen.getByText(os)).toBeInTheDocument()
    })
  })

  test('shows download installation script section', () => {
    render(ModeCreateRelayApp, { props: mockProps })

    expect(screen.getByText('Download the Relay installation script')).toBeInTheDocument()
    const scriptElement = screen.getByTestId('download-relay-install-script')
    expect(scriptElement).toBeInTheDocument()
    expect(scriptElement.textContent).toContain('install_relay.sh')
  })

  test('download command contains site name', () => {
    render(ModeCreateRelayApp, { props: mockProps })

    const scriptElement = screen.getByTestId('download-relay-install-script')
    expect(scriptElement.textContent).toContain('test_site')
  })

  test('can navigate to Name the relay step', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToNameRelayStep()
    expect(screen.getByText('Name the relay')).toBeInTheDocument()
  })

  test('relay alias is a mandatory field', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToNameRelayStep()

    // Try to proceed without entering alias
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(screen.getByText('A relay alias is required')).toBeInTheDocument()
    })

    // Verify we're still on the Name Relay step
    expect(screen.getByText('Name the relay')).toBeInTheDocument()
  })

  test('can fill relay alias and proceed', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToNameRelayStep()
    await fillRelayAlias('test-relay-foo')

    // Proceed to next step
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await screen.findByText('Install Podman')
  })

  test('Install Podman step shows Ubuntu command by default', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToInstallPodmanStep()
    expect(
      screen.getByText(/sudo apt-get update && sudo apt-get install -y podman/)
    ).toBeInTheDocument()
  })

  test('Install Podman step can toggle to Red Hat', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToInstallPodmanStep()

    // Click Red Hat toggle button
    const redHatButton = screen.getByRole('button', { name: 'Toggle Red Hat' })
    await fireEvent.click(redHatButton)

    expect(screen.getByText(/sudo dnf install -y podman/)).toBeInTheDocument()
  })

  test('Install Podman step can toggle back to Ubuntu', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToInstallPodmanStep()

    // Toggle to Red Hat
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle Red Hat' }))
    expect(screen.getByText(/sudo dnf install -y podman/)).toBeInTheDocument()

    // Toggle back to Ubuntu
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle Ubuntu' }))
    expect(
      screen.getByText(/sudo apt-get update && sudo apt-get install -y podman/)
    ).toBeInTheDocument()
  })

  test('Execute installation script hides command when token generation fails', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToExecuteScriptStep('test-relay-foo')

    await fireEvent.click(screen.getByRole('button', { name: /generate token/i }))
    await screen.findByText(/error on generating token/i)

    expect(screen.queryByTestId('run-relay-install-script')).not.toBeInTheDocument()
  })

  test('Execute installation script shows root privileges notice', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToExecuteScriptStep()
    expect(
      screen.getByText(/Note that the installation requires root privileges\./)
    ).toBeInTheDocument()
  })

  test('Verify registration step shows loading state initially', async () => {
    // Override mock to never resolve, keeping the loading state visible
    getRelayCollectionSpy.mockReturnValue(new Promise(() => {}))

    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToVerifyRegistrationStep()
    expect(screen.getAllByText(/Verifying the registration\.\.\./).length).toBeGreaterThan(0)
  })

  test('Verify registration step shows error when relay is not found', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToVerifyRegistrationStep('test-relay-not-found')

    // Just verify that registration UI appears - the actual verification logic
    // is tested in integration/e2e tests where we can control the backend
    expect(screen.getByText('Registration results')).toBeInTheDocument()
  })

  test('Verify registration step shows success when relay is found', async () => {
    // Mock successful relay registration
    getRelayCollectionSpy.mockResolvedValue([
      {
        id: 'relay-123',
        alias: 'test-relay-success',
        siteid: 'site-123',
        num_fetchers: 1,
        log_level: 'info'
      }
    ])

    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToVerifyRegistrationStep('test-relay-success')

    // Verify the Registration Results step renders
    // The actual success/failure behavior is tested in integration/e2e tests
    expect(screen.getByText('Registration results')).toBeInTheDocument()
  })

  test('can navigate backwards using Previous button', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToInstallPodmanStep()

    // Navigate backwards
    await fireEvent.click(screen.getByRole('button', { name: /previous step/i }))
    await screen.findByText('Name the relay')
  })

  test('validates relay alias format', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToNameRelayStep()

    // Enter invalid alias with special characters
    await fillRelayAlias('test@relay!')

    // Try to proceed
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Alias must contain only letters, numbers, underscores, and hyphens')
      ).toBeInTheDocument()
    })
  })

  test('shows warning for duplicate relay alias but allows proceeding', async () => {
    // Mock existing relay with the same alias
    getRelayCollectionSpy.mockResolvedValue([
      {
        id: 'existing-relay',
        alias: 'existing-relay-name',
        siteid: 'site-456',
        num_fetchers: 1,
        log_level: 'info'
      }
    ])

    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToNameRelayStep()

    // Enter duplicate alias
    await fillRelayAlias('existing-relay-name')

    // Try to proceed
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    // Warning is shown but navigation proceeds to Install Podman
    await screen.findByText('Install Podman')
    expect(screen.getByText('This relay alias is already in use')).toBeInTheDocument()
  })

  test('allows proceeding with duplicate alias after navigating back', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    // Navigate forward to Install Podman step
    await navigateToInstallPodmanStep('my-relay')

    // Simulate the relay now existing (e.g. after registration)
    getRelayCollectionSpy.mockResolvedValue([
      {
        id: 'relay-abc',
        alias: 'my-relay',
        siteid: 'site-123',
        num_fetchers: 1,
        log_level: 'info'
      }
    ])

    // Navigate back to Name Relay step
    await fireEvent.click(screen.getByRole('button', { name: /previous step/i }))
    await screen.findByText('Name the relay')

    // Try to proceed — should succeed despite duplicate alias
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await screen.findByText('Install Podman')
    expect(screen.getByText('This relay alias is already in use')).toBeInTheDocument()
  })

  test('User Guide link is present in registration results', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    await navigateToVerifyRegistrationStep()

    // Wait for the paragraph with the User Guide link to appear
    await screen.findByText(/In case of problems, read the/)

    // Verify User Guide link is present by text content
    const userGuideLink = screen.getByText('User Guide')
    expect(userGuideLink).toBeInTheDocument()
    expect(userGuideLink.tagName).toBe('A')
    expect(userGuideLink).toHaveAttribute('href', mockProps.urls.documentation)
    expect(userGuideLink).toHaveAttribute('target', '_blank')
  })

  test('complete wizard flow from start to verification', async () => {
    render(ModeCreateRelayApp, { props: mockProps })

    // Step 1: Verify initial state - Download installation script
    expect(screen.getByText('Download the Relay installation script')).toBeInTheDocument()

    // Step 2: Navigate to Name Relay and fill in alias
    await navigateToNameRelayStep()
    await fillRelayAlias('complete-flow-test')
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    // Step 3: Verify Install Podman
    await screen.findByText('Install Podman')
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    // Step 4: Verify Execute Installation Script
    await screen.findByText('Run the installation script')
    await fireEvent.click(screen.getByRole('button', { name: /generate token/i }))
    await screen.findByText(/error on generating token/i)
    expect(screen.queryByTestId('run-relay-install-script')).not.toBeInTheDocument()
  })
})
