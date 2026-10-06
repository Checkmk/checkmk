/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen, within } from '@testing-library/vue'
import type { AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'

import AgentDownloadApp from '@/setup/AgentDownloadApp.vue'

import {
  installCmds,
  kubernetesHelmCommand,
  kubernetesValues,
  registrationCmds,
  statusCmds
} from '../mode-host/agent-connection-test/fixtures'

const agentSlideout: AgentSlideout = {
  agent_install_cmds: installCmds,
  agent_registration_cmds: registrationCmds,
  agent_status_cmds: statusCmds,
  host_name: 'test-host',
  all_agents_url: 'https://example.test/all-agents',
  user_settings_url: 'https://example.test/user-settings',
  kubernetes_helm_command: kubernetesHelmCommand,
  kubernetes_values: kubernetesValues,
  kubernetes_doc_url: 'https://docs.example.test/kubernetes',
  save_host: false,
  host_exists: true,
  unbaked_fallback: null
}

const notRegisteredForHostOutput =
  "[agent] Error establishing TLS connection: The agent at 10.0.0.1 is not registered for this host. Check the host's IP address or register the agent for this host."

function renderApp(output: string, isPushMode = false) {
  render(AgentDownloadApp, {
    props: {
      user_id: 'test-user',
      output,
      site: 'test-site',
      server_per_site: [],
      agent_slideout: agentSlideout,
      is_push_mode: isPushMode
    },
    global: {
      stubs: {
        CmkTooltipProvider: { template: '<div><slot /></div>' },
        CmkTooltip: { props: ['open'], template: '<div v-if="open"><slot /></div>' },
        CmkTooltipTrigger: { template: '<div><slot /></div>' },
        CmkTooltipContent: { template: '<div><slot /></div>' },
        TooltipArrow: true
      }
    }
  })
}

describe('AgentDownloadApp', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
  })

  afterEach(() => {
    cleanup()
    localStorage.clear()
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  test('explains an agent that is not registered for this host', async () => {
    renderApp(notRegisteredForHostOutput)

    expect(await screen.findByText('Agent not registered for this host')).toBeInTheDocument()
  })

  test('opens the slide-in on the registration step for an agent not registered for this host', async () => {
    renderApp(notRegisteredForHostOutput)

    await userEvent.click(await screen.findByRole('button', { name: 'Register agent' }))

    expect(await screen.findByText('Register Checkmk agent')).toBeInTheDocument()
    const activeStep = screen.getByRole('listitem', { current: 'step' })
    expect(within(activeStep).getByRole('heading', { name: 'Register agent' })).toBeInTheDocument()
  })

  test('keeps the generic hint in push mode', async () => {
    renderApp(notRegisteredForHostOutput, true)

    expect(
      await screen.findByText('Agent communication failed during service discovery')
    ).toBeInTheDocument()
    expect(screen.queryByText('Agent not registered for this host')).not.toBeInTheDocument()
  })
})
