/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, screen } from '@testing-library/vue'

import DownloadMsiInstaller from '@/mode-relay/add-relay-configuration-steps/DownloadMsiInstaller.vue'

import { mountWithWizardContext } from '../helpers'

const baseProps = {
  index: 1,
  isCompleted: () => false,
  domain: 'checkmk.example.com',
  siteName: 'my_site',
  serverPort: null
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('DownloadMsiInstaller', () => {
  test('download command is an Invoke-WebRequest PowerShell command', () => {
    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    const cmd = screen.getByLabelText('Download relay MSI installer command')
    expect(cmd.textContent).toContain('Invoke-WebRequest')
  })

  test('download command targets CheckmkRelayInstaller.msi', () => {
    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    const cmd = screen.getByLabelText('Download relay MSI installer command')
    expect(cmd.textContent).toContain('CheckmkRelayInstaller.msi')
  })

  test('download command contains domain without port when serverPort is null', () => {
    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    const cmd = screen.getByLabelText('Download relay MSI installer command')
    expect(cmd.textContent).toContain('//checkmk.example.com/')
    expect(cmd.textContent).not.toContain('checkmk.example.com:')
  })

  test('download command contains domain:port when serverPort is provided', () => {
    mountWithWizardContext(DownloadMsiInstaller, { ...baseProps, serverPort: 5000 })

    const cmd = screen.getByLabelText('Download relay MSI installer command')
    expect(cmd.textContent).toContain('checkmk.example.com:5000')
  })

  test('download command contains site name', () => {
    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    const cmd = screen.getByLabelText('Download relay MSI installer command')
    expect(cmd.textContent).toContain('my_site')
  })

  test('shows insecure protocol warning when protocol is http', () => {
    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    expect(screen.getByText(/Insecure connection detected/)).toBeInTheDocument()
  })

  test('no insecure protocol warning when protocol is https', () => {
    vi.stubGlobal('location', { protocol: 'https:' })

    mountWithWizardContext(DownloadMsiInstaller, baseProps)

    expect(screen.queryByText(/Insecure connection detected/)).not.toBeInTheDocument()
  })
})
