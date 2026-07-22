/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, screen } from '@testing-library/vue'

import InstallWSL2 from '@/mode-relay/add-relay-configuration-steps/InstallWSL2.vue'

import { mountWithWizardContext } from '../helpers'

const baseProps = { index: 1, isCompleted: () => false }

afterEach(cleanup)

describe('InstallWSL2', () => {
  test('shows the WSL2 installation command', () => {
    mountWithWizardContext(InstallWSL2, baseProps)

    expect(screen.getByTestId('install-wsl2-command').textContent).toContain(
      'wsl --install --web-download --no-distribution; Restart-Computer -Confirm'
    )
  })

  test('shows restart prompt warning', () => {
    mountWithWizardContext(InstallWSL2, baseProps)

    expect(screen.getByText(/prompt you to restart the computer/)).toBeInTheDocument()
  })

  test('shows nested virtualization notice', () => {
    mountWithWizardContext(InstallWSL2, baseProps)

    expect(screen.getByText(/must support nested virtualization/)).toBeInTheDocument()
  })
})
