/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/vue'
import { Api } from 'cmk-ui-library/lib/api-client'

import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

import { contentProps, installCmds } from './fixtures'

const TOKEN = 'test-ott-value'

const DOWNLOAD_TOKEN_URI = 'domain-types/agent_download_token/collections/all'
const REGISTRATION_TOKEN_URI = 'domain-types/agent_registration_token/collections/all'

function mockTokenGeneration(domainType: 'download_token' | 'registration_token') {
  return vi.spyOn(Api.prototype, 'post').mockResolvedValue({
    id: TOKEN,
    title: 'Test Token',
    domainType,
    extensions: {
      comment: '',
      issued_at: new Date(),
      expires_at: null,
      host_name: contentProps.hostName
    }
  })
}

function mockFailingTokenGeneration() {
  vi.spyOn(Api.prototype, 'post').mockRejectedValue(new Error('token generation failed'))
}

function renderContent(overrides: Partial<typeof contentProps> = {}) {
  return render(AgentSlideOutContent, {
    props: { ...contentProps, ...overrides },
    global: { stubs: { teleport: true } }
  })
}

/**
 * Select a tab in the "type of system" strip. `userEvent` is required here:
 * reka's TabsTrigger activates on focus, which `fireEvent.click` does not do.
 */
async function selectTab(name: string) {
  await userEvent.click(screen.getByRole('tab', { name }))
}

/** Switch a package or shell variant in a toggle button group. */
async function toggle(label: string) {
  await fireEvent.click(within(panel()).getByRole('button', { name: `Toggle ${label}` }))
}

/**
 * The panel of the selected tab. Hidden panels stay mounted, so every DOM
 * query has to be scoped to the visible one.
 */
function panel(): HTMLElement {
  const visible = document.querySelector('[role="tabpanel"]:not([hidden])')
  if (visible === null) {
    throw new Error('no tab panel is visible')
  }
  return visible as HTMLElement
}

/** The `<li>` of a wizard step, addressed by its heading. */
function step(heading: string): HTMLElement {
  const element = within(panel()).getByText(heading).closest('li')
  if (element === null) {
    throw new Error(`step "${heading}" is not inside an <li>`)
  }
  return element
}

function activeStepHeading(): string {
  const current = panel().querySelector('li[aria-current="step"]')
  if (current === null) {
    throw new Error('no step is marked as current')
  }
  return current.querySelector('h1, h2, h3, h4, h5, h6')?.textContent?.trim() ?? ''
}

/** Text of every code block in the visible panel, in document order. */
function codeTexts(): string[] {
  return [...panel().querySelectorAll('pre code')].map((el) => el.textContent ?? '')
}

async function generateToken() {
  await fireEvent.click(within(panel()).getByRole('button', { name: /generate one-time token/i }))
  await within(panel()).findByText(/Successfully generated one-time token/)
}

describe('AgentSlideOutContent', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  test('offers the four platform tabs in a fixed order', () => {
    renderContent()

    expect(screen.getAllByRole('tab').map((tab) => tab.textContent?.trim())).toEqual([
      'Windows',
      'Linux',
      'Solaris',
      'AIX'
    ])
  })

  test('opens on the Linux tab', () => {
    renderContent()

    expect(screen.getByRole('tab', { name: 'Linux' })).toHaveAttribute('aria-selected', 'true')
  })

  test('shows three wizard steps outside push mode', () => {
    renderContent({ isPushMode: false })

    expect(step('Save host')).toBeInTheDocument()
    expect(step('Download and install')).toBeInTheDocument()
    expect(step('Register agent')).toBeInTheDocument()
    expect(within(panel()).queryByText('Test connection')).not.toBeInTheDocument()
  })

  test('adds the Test connection step in push mode', () => {
    renderContent({ isPushMode: true })

    expect(step('Test connection')).toBeInTheDocument()
  })

  test('starts on Save host when the host still has to be saved', () => {
    renderContent({ saveHost: true })

    expect(activeStepHeading()).toBe('Save host')
  })

  test('starts on Download and install when no agent is installed yet', () => {
    renderContent({ saveHost: false, agentInstalled: false })

    expect(activeStepHeading()).toBe('Download and install')
  })

  test('starts on Register agent when the agent is already installed', () => {
    renderContent({ saveHost: false, agentInstalled: true })

    expect(activeStepHeading()).toBe('Register agent')
  })

  test('asks for a download token for the selected site', async () => {
    const post = mockTokenGeneration('download_token')
    renderContent()

    await generateToken()

    expect(post).toHaveBeenCalledWith(DOWNLOAD_TOKEN_URI, {
      site_id: contentProps.siteId,
      expires_at: expect.any(Date)
    })
  })

  test('asks for a registration token for this host', async () => {
    const post = mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true })

    await generateToken()

    expect(post).toHaveBeenCalledWith(REGISTRATION_TOKEN_URI, {
      host: contentProps.hostName,
      site_id: contentProps.siteId,
      comment: expect.any(String),
      expires_at: expect.any(Date)
    })
  })

  test('keeps each platform on its own step', async () => {
    mockTokenGeneration('download_token')
    renderContent()
    await generateToken()
    await fireEvent.click(within(panel()).getByRole('button', { name: /next step/i }))
    expect(activeStepHeading()).toBe('Register agent')

    await selectTab('Windows')
    expect(activeStepHeading()).toBe('Download and install')

    await selectTab('Linux')
    expect(activeStepHeading()).toBe('Register agent')
  })

  test('keeps a generated token when another platform is inspected', async () => {
    mockTokenGeneration('download_token')
    renderContent()
    await generateToken()

    await selectTab('Windows')
    await selectTab('Linux')

    expect(within(panel()).getByText(/Successfully generated one-time token/)).toBeInTheDocument()
  })

  test('substitutes site macros and the download token into the install command', async () => {
    mockTokenGeneration('download_token')
    renderContent()

    await generateToken()

    expect(codeTexts().join('\n')).toContain(
      `deb-install ${contentProps.siteServer}/${contentProps.siteId} 0:${TOKEN}`
    )
  })

  test('offers the Linux package variants and switches the install command', async () => {
    mockTokenGeneration('download_token')
    renderContent()

    await toggle('RPM')
    await generateToken()

    expect(codeTexts().join('\n')).toContain('rpm-install')
    expect(codeTexts().join('\n')).not.toContain('deb-install')
  })

  test('warns about extracting into the root directory for the TGZ package', async () => {
    mockTokenGeneration('download_token')
    renderContent()

    await toggle('TGZ')
    await generateToken()

    expect(
      within(panel()).getByText(/extracts files directly into the root directory/)
    ).toBeInTheDocument()
    expect(codeTexts().join('\n')).toContain('tgz-download')
    expect(codeTexts().join('\n')).toContain('tgz-extract')
  })

  test('discards the generated token when the package selection changes', async () => {
    mockTokenGeneration('download_token')
    renderContent()
    await generateToken()

    await toggle('RPM')

    expect(
      within(panel()).queryByText(/Successfully generated one-time token/)
    ).not.toBeInTheDocument()
  })

  test('offers the Windows shell variants and switches both commands', async () => {
    mockTokenGeneration('download_token')
    renderContent()
    await selectTab('Windows')
    await generateToken()

    expect(codeTexts().join('\n')).toContain('ps-download')
    expect(codeTexts().join('\n')).toContain('ps-install')

    await toggle('Command Prompt')

    expect(codeTexts().join('\n')).toContain('cmd-download')
    expect(codeTexts().join('\n')).toContain('cmd-install')
    expect(codeTexts().join('\n')).not.toContain('ps-download')
    expect(codeTexts().join('\n')).not.toContain('ps-install')
  })

  test('restores the shell preference from local storage', async () => {
    localStorage.setItem('slideInSelectedVariantId', JSON.stringify('cmd'))
    mockTokenGeneration('download_token')
    renderContent()
    await selectTab('Windows')
    await generateToken()

    expect(codeTexts().join('\n')).toContain('cmd-install')
  })

  test('resolves {{SERVER}} to the agent receiver host:port for registration', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true })

    await generateToken()

    expect(codeTexts().join('\n')).toContain('--server monitoring.example.test:8000')
  })

  test('replaces the registration user with the generated token', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true })

    await generateToken()

    const registrationCommand = codeTexts().find((text) => text.includes('linux-register'))
    expect(registrationCommand).toContain(`--ott 0:${TOKEN}`)
    expect(registrationCommand).not.toContain('--user agent_registration')
  })

  test('keeps the registration user command in the troubleshooting section', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true })
    await generateToken()

    const fallback = within(panel())
      .getAllByText(/--user agent_registration/)
      .map((el) => el.closest('pre'))
      .at(-1)
    expect(fallback).not.toBeVisible()

    await fireEvent.click(
      within(panel()).getByText(/Troubleshooting registration issues/, {
        selector: 'button, div, span'
      })
    )

    expect(fallback).toBeVisible()
  })

  test('warns when the agent receiver port could not be determined', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true, agentReceiverPortIsDefault: true })

    await generateToken()

    expect(within(panel()).getByText(/uses the default port \(8000\)/)).toBeInTheDocument()
  })

  test('shows the unbaked fallback commands instead of a download token', () => {
    renderContent({
      unbakedFallback: {
        intro: 'Use the following command to download an agent package:',
        commands: ['wget {{SERVER}}/{{SITE}}/agent.rpm', 'wget {{SERVER}}/{{SITE}}/agent.deb']
      }
    })

    expect(within(panel()).getByText(/Use the following command to download/)).toBeInTheDocument()
    expect(codeTexts().join('\n')).toContain(
      `wget ${contentProps.siteServer}/${contentProps.siteId}/agent.rpm`
    )
    expect(
      within(panel()).queryByRole('button', { name: /generate one-time token/i })
    ).not.toBeInTheDocument()
  })

  test('offers a close-and-review action when saving the host failed', () => {
    renderContent({ saveHost: true, setupError: true })

    expect(within(panel()).getByRole('button', { name: /Close & review/ })).toBeInTheDocument()
    expect(
      within(panel()).queryByRole('button', { name: /Save host & next step/ })
    ).not.toBeInTheDocument()
  })

  test('submits the edit-host form when the host is saved', async () => {
    const formSubmit = vi.fn()
    vi.stubGlobal('cmk', { page_menu: { form_submit: formSubmit } })
    renderContent({ saveHost: true, agentInstalled: true })

    await fireEvent.click(within(panel()).getByRole('button', { name: /Save host & next step/ }))

    expect(formSubmit).toHaveBeenCalledWith('edit_host', 'save_and_edit')
  })

  test('remembers tab, package and agent state across the save-host reload', async () => {
    vi.stubGlobal('cmk', { page_menu: { form_submit: vi.fn() } })
    renderContent({ saveHost: true, agentInstalled: true })

    await fireEvent.click(screen.getByRole('button', { name: /Save host & next step/ }))

    expect(sessionStorage.getItem('reopenSlideIn')).toBe('true')
    expect(sessionStorage.getItem('slideInTabState')).toBe('linux')
    expect(sessionStorage.getItem('slideInModelState')).toBe('deb')
    expect(sessionStorage.getItem('slideInAgentInstalled')).toBe('true')
  })

  test('reopens on the tab remembered before the save-host reload', () => {
    sessionStorage.setItem('slideInTabState', 'aix')

    renderContent()

    expect(screen.getByRole('tab', { name: 'AIX' })).toHaveAttribute('aria-selected', 'true')
  })

  test('finishes on the register step outside push mode', () => {
    renderContent({ agentInstalled: true, isPushMode: false })

    expect(
      within(step('Register agent')).getByRole('button', {
        name: new RegExp(contentProps.closeButtonTitle)
      })
    ).toBeInTheDocument()
  })

  test('shows the status command on the last step in push mode', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ agentInstalled: true, isPushMode: true })
    await generateToken()

    await fireEvent.click(within(panel()).getByRole('button', { name: /next step/i }))

    expect(codeTexts().join('\n')).toContain('linux-status')
  })

  test('hides the registration command when token generation fails', async () => {
    mockFailingTokenGeneration()
    renderContent({ agentInstalled: true, isPushMode: false })

    await fireEvent.click(within(panel()).getByRole('button', { name: /generate one-time token/i }))
    await within(panel()).findByText(/Error generating one-time token/)

    // The troubleshooting fallback stays in the DOM on purpose; what must be
    // gone is the second, token-bearing command block.
    expect(codeTexts().filter((text) => text.includes('linux-register'))).toHaveLength(1)
    expect(
      within(panel()).queryByText(/run this command on your Linux host/)
    ).not.toBeInTheDocument()
    expect(codeTexts().join('\n')).not.toContain('--ott 0:')
    // Registering with the agent_registration user is a legitimate way out, so
    // the step must stay finishable after a failed token.
    expect(
      within(step('Register agent')).getByRole('button', {
        name: new RegExp(contentProps.closeButtonTitle)
      })
    ).toBeEnabled()
  })

  test('offers a retry after token generation failed', async () => {
    mockFailingTokenGeneration()
    renderContent({ agentInstalled: true, isPushMode: false })
    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Error generating one-time token/)

    await fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(screen.getByRole('button', { name: /generate one-time token/i })).toBeInTheDocument()
  })

  test('says why the registration command is hidden after a failed token', async () => {
    mockFailingTokenGeneration()
    renderContent({ agentInstalled: true, isPushMode: false })

    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Error generating one-time token/)

    expect(
      screen.getByText(/hidden until a token has been generated successfully/)
    ).toBeInTheDocument()
  })

  test('stays finishable after retrying a failed token', async () => {
    mockFailingTokenGeneration()
    renderContent({ agentInstalled: true, isPushMode: false })
    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Error generating one-time token/)

    await fireEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(
      within(step('Register agent')).getByRole('button', {
        name: new RegExp(contentProps.closeButtonTitle)
      })
    ).toBeEnabled()
  })

  test('does not carry a failed attempt over to another platform', async () => {
    mockFailingTokenGeneration()
    renderContent()
    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Error generating one-time token/)

    await selectTab('Windows')

    expect(
      within(step('Download and install')).getByRole('button', { name: /next step/i })
    ).toBeDisabled()
  })

  test('does not carry a failed attempt over the previous button', async () => {
    const post = mockTokenGeneration('download_token')
    post.mockRejectedValueOnce(new Error('token generation failed'))
    renderContent({ agentInstalled: true, isPushMode: false })
    await fireEvent.click(screen.getByRole('button', { name: /generate one-time token/i }))
    await screen.findByText(/Error generating one-time token/)

    // Back to the install step and forward again: the registration step has
    // not been attempted since, so it must ask for a token as it did before.
    await fireEvent.click(
      within(step('Register agent')).getByRole('button', { name: /previous step/i })
    )
    await generateToken()
    await fireEvent.click(
      within(step('Download and install')).getByRole('button', { name: /next step/i })
    )

    expect(
      within(step('Register agent')).getByRole('button', {
        name: new RegExp(contentProps.closeButtonTitle)
      })
    ).toBeDisabled()
  })

  test('hides the install command when token generation fails', async () => {
    mockFailingTokenGeneration()
    renderContent()

    await fireEvent.click(within(panel()).getByRole('button', { name: /generate one-time token/i }))
    await within(panel()).findByText(/Error generating one-time token/)

    expect(codeTexts().join('\n')).not.toContain('deb-install')
    expect(codeTexts().join('\n')).not.toContain('[AGENT_DOWNLOAD_OTT]')
  })

  test('offers the legacy agent link when no packages are available', () => {
    renderContent({
      legacyAgentUrl: 'https://docs.example.test/legacy-agent',
      agentInstallCmds: { ...installCmds, linux_deb: '', linux_rpm: '', linux_tgz_download: '' }
    })

    expect(
      within(panel()).getByRole('link', { name: /Install the legacy Checkmk agent/ })
    ).toBeInTheDocument()
    expect(codeTexts().join('\n')).not.toContain('-install')
  })

  test('asks for no download token when no command needs one', () => {
    renderContent({
      agentInstallCmds: {
        ...installCmds,
        linux_deb: 'deb-install {{SERVER}}/{{SITE}}',
        linux_rpm: '',
        linux_tgz_download: ''
      }
    })

    expect(
      within(panel()).queryByRole('button', { name: /generate one-time token/i })
    ).not.toBeInTheDocument()
    expect(codeTexts().join('\n')).toContain('deb-install')
  })

  test('offers a Kubernetes tab in push mode', () => {
    renderContent({ isPushMode: true })

    expect(screen.getByRole('tab', { name: 'Kubernetes' })).toBeInTheDocument()
  })

  test('hands out the Helm command with the generated registration token', async () => {
    mockTokenGeneration('registration_token')
    renderContent({ isPushMode: true })
    await selectTab('Kubernetes')

    await generateToken()

    expect(codeTexts().join('\n')).toContain(`push.registrationToken=0:${TOKEN}`)
  })
})
