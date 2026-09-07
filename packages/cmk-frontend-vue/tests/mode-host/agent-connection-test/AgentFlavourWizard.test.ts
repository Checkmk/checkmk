/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen } from '@testing-library/vue'

import AgentFlavourWizard from '@/mode-host/agent-connection-test/components/AgentFlavourWizard.vue'
import type { HostMacros } from '@/mode-host/agent-connection-test/lib/commandTemplate'
import type { AgentFlavour } from '@/mode-host/agent-connection-test/lib/types'

const macros: HostMacros = {
  hostName: 'test-host',
  siteId: 'test-site',
  downloadServer: 'https://monitoring.example.test',
  registrationServer: 'monitoring.example.test:8000'
}

/**
 * A flavour that is only registered — no package to install and no status
 * command. It exists to show that a step set differing from the usual one is a
 * matter of data, without a change to any component.
 */
const registrationOnly: AgentFlavour = {
  id: 'registration-only',
  title: 'Registration only',
  register: {
    msg: 'Run this command to register.',
    commands: {
      kind: 'single',
      block: { command: 'deploy --hostname {{HOSTNAME}} --user agent_registration' }
    }
  }
}

const baseProps = {
  macros,
  saveHost: false,
  hostExists: true,
  setupError: false,
  agentInstalled: false,
  isPushMode: true,
  hostName: macros.hostName,
  siteId: macros.siteId,
  userSettingsUrl: 'https://example.test/user-settings',
  closeButtonTitle: 'Close slideout',
  agentReceiverPortIsDefault: false,
  shellId: ''
}

function renderWizard(flavour: AgentFlavour) {
  return render(AgentFlavourWizard, {
    props: { ...baseProps, flavour },
    global: { stubs: { teleport: true } }
  })
}

function stepHeadings(): string[] {
  return [...document.querySelectorAll('li')]
    .map((li) => li.querySelector('h1, h2, h3, h4, h5, h6')?.textContent?.trim() ?? '')
    .filter((heading) => heading !== '')
}

describe('AgentFlavourWizard', () => {
  afterEach(() => {
    cleanup()
  })

  test('shows only the steps a flavour declares', () => {
    renderWizard(registrationOnly)

    expect(stepHeadings()).toEqual(['Save host', 'Register agent'])
  })

  test('starts on the registration step when there is nothing to install', () => {
    renderWizard(registrationOnly)

    expect(screen.getByText('Register agent').closest('li')).toHaveAttribute('aria-current', 'step')
  })

  test('finishes on the registration step even in push mode', () => {
    renderWizard(registrationOnly)

    expect(
      screen.getByRole('button', { name: new RegExp(baseProps.closeButtonTitle) })
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /next step/i })).not.toBeInTheDocument()
  })

  test('waits for a token before the step can be finished', () => {
    renderWizard(registrationOnly)

    expect(screen.getByRole('button', { name: /generate one-time token/i })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: new RegExp(baseProps.closeButtonTitle) })
    ).toBeDisabled()
  })

  test('offers no troubleshooting hint when the flavour declares none', () => {
    renderWizard(registrationOnly)

    expect(screen.queryByText(/Troubleshooting registration issues/)).not.toBeInTheDocument()
  })
})
