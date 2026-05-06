/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, screen } from '@testing-library/vue'

import InstallPodman from '@/mode-relay/add-relay-configuration-steps/InstallPodman.vue'

import { mountWithWizardContext } from '../helpers'

const baseProps = { index: 1, isCompleted: () => false }

afterEach(cleanup)

describe('InstallPodman', () => {
  test('shows Ubuntu apt command by default', () => {
    mountWithWizardContext(InstallPodman, baseProps)

    expect(screen.getByTestId('install-podman-command').textContent).toContain(
      'sudo apt-get update && sudo apt-get install -y podman'
    )
  })

  test('toggling to Red Hat shows dnf command', async () => {
    mountWithWizardContext(InstallPodman, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: 'Toggle Red Hat' }))

    expect(screen.getByTestId('install-podman-command').textContent).toContain(
      'sudo dnf install -y podman'
    )
  })

  test('toggling back to Ubuntu restores apt command', async () => {
    mountWithWizardContext(InstallPodman, baseProps)

    await fireEvent.click(screen.getByRole('button', { name: 'Toggle Red Hat' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle Ubuntu' }))

    expect(screen.getByTestId('install-podman-command').textContent).toContain(
      'sudo apt-get update && sudo apt-get install -y podman'
    )
  })
})
