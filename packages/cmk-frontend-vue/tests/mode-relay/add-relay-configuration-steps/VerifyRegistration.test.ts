/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, screen, waitFor } from '@testing-library/vue'

import VerifyRegistration from '@/mode-relay/add-relay-configuration-steps/VerifyRegistration.vue'
import * as relayClient from '@/mode-relay/relay-client'

import { mountWithWizardContext } from '../helpers'

const baseProps = {
  index: 1,
  isCompleted: () => false,
  relayAlias: 'test-relay',
  documentationUrl: 'https://docs.checkmk.com/relay'
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('VerifyRegistration', () => {
  test('shows loading state while API is pending', () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockReturnValue(new Promise(() => {}))

    mountWithWizardContext(VerifyRegistration, baseProps)

    expect(screen.getByText('Verifying the registration...')).toBeInTheDocument()
  })

  test('shows success alert when relay is found by alias', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([
      { id: 'relay-123', alias: 'test-relay', siteid: 'site-1', num_fetchers: 1, log_level: 'info' }
    ])

    mountWithWizardContext(VerifyRegistration, baseProps)

    await screen.findByText('Relay registered and saved successfully!')
  })

  test('emits relayId when relay is found', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([
      { id: 'relay-123', alias: 'test-relay', siteid: 'site-1', num_fetchers: 1, log_level: 'info' }
    ])

    const { emitted } = mountWithWizardContext(VerifyRegistration, baseProps)

    await screen.findByText('Relay registered and saved successfully!')
    expect(emitted()['update:modelValue']).toEqual([['relay-123']])
  })

  test('shows failure alert when relay is not found', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([])

    mountWithWizardContext(VerifyRegistration, baseProps)

    await screen.findByText("Registration failed and Relay couldn't be saved.")
  })

  test('shows error message when API throws', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockRejectedValue(new Error('Server error'))

    mountWithWizardContext(VerifyRegistration, baseProps)

    await screen.findByText('Server error')
  })

  test('User Guide link has correct href and opens in new tab', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([])

    mountWithWizardContext(VerifyRegistration, baseProps)

    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'User Guide' })
      expect(link).toHaveAttribute('href', 'https://docs.checkmk.com/relay')
      expect(link).toHaveAttribute('target', '_blank')
    })
  })

  test('does not call getRelayCollection when step is not selected', () => {
    const spy = vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([])

    mountWithWizardContext(VerifyRegistration, baseProps, {
      isSelected: () => false
    })

    expect(spy).not.toHaveBeenCalled()
  })
})
