/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/vue'

import NameRelay from '@/mode-relay/add-relay-configuration-steps/NameRelay.vue'
import * as relayClient from '@/mode-relay/relay-client'

import { mountWithWizardContext } from '../helpers'

const baseProps = {
  index: 1,
  isCompleted: () => false,
  aliasValidationRegex: '^[a-zA-Z0-9_-]+$',
  aliasValidationRegexHelp: 'Alias must contain only letters, numbers, underscores, and hyphens'
}

beforeEach(() => {
  vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([])
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('NameRelay', () => {
  test('errors are not shown before first submit attempt', () => {
    mountWithWizardContext(NameRelay, baseProps)

    expect(screen.queryByText('A relay alias is required')).not.toBeInTheDocument()
  })

  test('empty alias shows required error and blocks navigation', async () => {
    const { navigation } = mountWithWizardContext(NameRelay, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(screen.getByText('A relay alias is required')).toBeInTheDocument()
    })
    expect(navigation.next).not.toHaveBeenCalled()
  })

  test('alias failing regex shows regex help text and blocks navigation', async () => {
    const { navigation } = mountWithWizardContext(NameRelay, baseProps)

    await userEvent.type(screen.getByRole('textbox'), 'invalid alias!')
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Alias must contain only letters, numbers, underscores, and hyphens')
      ).toBeInTheDocument()
    })
    expect(navigation.next).not.toHaveBeenCalled()
  })

  test('valid alias with no duplicates calls navigation.next', async () => {
    const { navigation } = mountWithWizardContext(NameRelay, baseProps)

    await userEvent.type(screen.getByRole('textbox'), 'my-relay')
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(navigation.next).toHaveBeenCalled()
    })
  })

  test('duplicate alias shows warning but still calls navigation.next', async () => {
    vi.spyOn(relayClient, 'getRelayCollection').mockResolvedValue([
      { id: 'existing', alias: 'my-relay', siteid: 'site-1', num_fetchers: 1, log_level: 'info' }
    ])
    const { navigation } = mountWithWizardContext(NameRelay, baseProps)

    await userEvent.type(screen.getByRole('textbox'), 'my-relay')
    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    await waitFor(() => {
      expect(screen.getByText('This relay alias is already in use')).toBeInTheDocument()
    })
    expect(navigation.next).toHaveBeenCalled()
  })
})
