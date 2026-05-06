/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, screen } from '@testing-library/vue'

import { Api } from '@/lib/api-client'

import RunMsiInstaller from '@/mode-relay/add-relay-configuration-steps/RunMsiInstaller.vue'

import { mountWithWizardContext } from '../helpers'

const baseProps = {
  index: 1,
  isCompleted: () => false,
  relayAlias: 'test-relay',
  siteName: 'my_site',
  domain: 'checkmk.example.com',
  agentReceiverPort: 8000,
  siteVersion: '2.5.0'
}

const mockTokenResponse = {
  id: 'mock-token-abc',
  title: 'Token',
  domainType: 'relay_registration_token',
  extensions: { comment: '', issued_at: new Date(), expires_at: null, host_name: '' }
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('RunMsiInstaller', () => {
  test('shows administrator privileges notice (not root)', () => {
    mountWithWizardContext(RunMsiInstaller, baseProps)

    expect(
      screen.getByText(/Note that the installation requires administrator privileges/)
    ).toBeInTheDocument()
    expect(screen.queryByText(/root privileges/)).not.toBeInTheDocument()
  })

  test('install command is not present before token generation', () => {
    mountWithWizardContext(RunMsiInstaller, baseProps)

    expect(screen.queryByTestId('run-msi-installer-command')).not.toBeInTheDocument()
  })

  test('shows error and hides command when token generation fails', async () => {
    vi.spyOn(Api.prototype, 'post').mockRejectedValue(new Error('Network error'))
    mountWithWizardContext(RunMsiInstaller, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/error generating one-time token/i)

    expect(screen.queryByTestId('run-msi-installer-command')).not.toBeInTheDocument()
  })

  test('shows install command after successful token generation', async () => {
    vi.spyOn(Api.prototype, 'post').mockResolvedValue(mockTokenResponse)
    mountWithWizardContext(RunMsiInstaller, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/This token remains valid for/)

    expect(screen.getByTestId('run-msi-installer-command')).toBeInTheDocument()
  })

  test('install command uses msiexec and contains relay alias, domain, port, site name, version, token', async () => {
    vi.spyOn(Api.prototype, 'post').mockResolvedValue(mockTokenResponse)
    mountWithWizardContext(RunMsiInstaller, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/This token remains valid for/)

    const cmd = screen.getByTestId('run-msi-installer-command').textContent ?? ''
    expect(cmd).toContain('msiexec')
    expect(cmd).toContain('test-relay')
    expect(cmd).toContain('checkmk.example.com:8000')
    expect(cmd).toContain('my_site')
    expect(cmd).toContain('2.5.0')
    expect(cmd).toContain('mock-token-abc')
  })

  test('Next button is blocked until a valid token is generated', async () => {
    const { navigation } = mountWithWizardContext(RunMsiInstaller, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: /next step/i }))

    expect(navigation.next).not.toHaveBeenCalled()
  })
})
