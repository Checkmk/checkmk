/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, screen } from '@testing-library/vue'

import InstallWSL2 from '@/mode-relay/add-relay-configuration-steps/InstallWSL2.vue'

import { mountWithWizardContext } from '../helpers'

const baseProps = { index: 1, isCompleted: () => false }

afterEach(cleanup)

describe('InstallWSL2', () => {
  test('shows the WSL2 installation script', async () => {
    mountWithWizardContext(InstallWSL2, baseProps)

    expect(screen.getByTestId('install-wsl2-command').textContent).toContain(
      'Enable-WindowsOptionalFeature'
    )

    // The script is longer than CmkCode's collapsed preview, so expand it first.
    await fireEvent.click(screen.getByText('Show more'))

    expect(screen.getByTestId('install-wsl2-command').textContent).toContain(
      'Restart-Computer -Force'
    )
  })

  test('shows automatic reboot warning', () => {
    mountWithWizardContext(InstallWSL2, baseProps)

    expect(screen.getByText(/will restart the computer/)).toBeInTheDocument()
  })
})
