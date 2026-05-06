/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, screen } from '@testing-library/vue'

import InstallRelay from '@/mode-relay/add-relay-configuration-steps/InstallRelay.vue'

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

describe('InstallRelay', () => {
  test('download command contains site name', () => {
    mountWithWizardContext(InstallRelay, baseProps)

    const cmd = screen.getByLabelText('Download relay install script command')
    expect(cmd.textContent).toContain('my_site')
  })

  test('download command contains domain without port when serverPort is null', () => {
    mountWithWizardContext(InstallRelay, baseProps)

    const cmd = screen.getByLabelText('Download relay install script command')
    expect(cmd.textContent).toContain('//checkmk.example.com/')
    expect(cmd.textContent).not.toContain('checkmk.example.com:')
  })

  test('download command contains domain:port when serverPort is provided', () => {
    mountWithWizardContext(InstallRelay, { ...baseProps, serverPort: 5000 })

    const cmd = screen.getByLabelText('Download relay install script command')
    expect(cmd.textContent).toContain('checkmk.example.com:5000')
  })

  test('download command references install_relay.sh', () => {
    mountWithWizardContext(InstallRelay, baseProps)

    const cmd = screen.getByLabelText('Download relay install script command')
    expect(cmd.textContent).toContain('install_relay.sh')
  })

  test('shows insecure protocol warning when protocol is http', () => {
    // jsdom defaults to http: so no stub needed
    mountWithWizardContext(InstallRelay, baseProps)

    expect(screen.getByText(/Insecure connection detected/)).toBeInTheDocument()
  })

  test('no insecure protocol warning when protocol is https', () => {
    vi.stubGlobal('location', { protocol: 'https:' })

    mountWithWizardContext(InstallRelay, baseProps)

    expect(screen.queryByText(/Insecure connection detected/)).not.toBeInTheDocument()
  })
})
