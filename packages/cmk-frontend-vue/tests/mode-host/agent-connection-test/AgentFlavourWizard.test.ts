/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
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

  test('offers the secret check instead of the registration user for a cluster', async () => {
    renderWizard({
      ...registrationOnly,
      register: { ...registrationOnly.register!, troubleshooting: 'kubernetes-secret' }
    })

    await userEvent.click(
      screen.getByRole('button', { name: /Check whether the registration was successful/ })
    )

    expect(screen.getByText('cmk-signed-push-cert')).toBeVisible()
    expect(screen.queryByText(/Authenticate with the registration user/)).not.toBeInTheDocument()
  })

  test("shows the flavour's own registration explanation instead of the generic one", () => {
    renderWizard({
      ...registrationOnly,
      register: { ...registrationOnly.register!, intro: 'Trust the in-cluster components.' }
    })

    expect(screen.getByText('Trust the in-cluster components.')).toBeInTheDocument()
    expect(screen.queryByText(/Agent Controller/)).not.toBeInTheDocument()
  })

  test('shows a configuration block pointing at the agent receiver', () => {
    renderWizard({
      ...registrationOnly,
      register: {
        ...registrationOnly.register!,
        config: { code: { title: 'values.yaml', text: 'url: https://{{SERVER}}/{{SITE}}' } }
      }
    })

    expect(screen.getByText('values.yaml')).toBeInTheDocument()
    expect(
      screen.getByText('url: https://monitoring.example.test:8000/test-site')
    ).toBeInTheDocument()
  })
})
