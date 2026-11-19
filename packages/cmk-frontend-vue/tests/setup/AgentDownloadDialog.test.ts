/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import AgentDownloadDialog from '@/setup/AgentDownloadDialog.vue'

import {
  FakeResizeObserver,
  deliverSize,
  useFakeResizeObserver
} from '@tests/lib/fakeResizeObserver'
import {
  commandPlaceholders,
  installCmds,
  kubernetesHelmCommand,
  kubernetesValues,
  registrationCmds,
  statusCmds
} from '@tests/mode-host/agent-connection-test/fixtures'

const HINT_TITLE = 'Agent communication failed during service discovery'

const agentSlideout: AgentSlideout = {
  agent_install_cmds: installCmds,
  agent_registration_cmds: registrationCmds,
  agent_status_cmds: statusCmds,
  command_placeholders: commandPlaceholders,
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

function renderDialog(container?: HTMLElement) {
  return render(AgentDownloadDialog, {
    ...(container ? { container } : {}),
    props: {
      userId: 'test-user',
      dialogTitle: HINT_TITLE as TranslatedString,
      dialogMessage: 'The agent might not be installed.' as TranslatedString,
      slideInTitle: 'Install Checkmk agent' as TranslatedString,
      slideInButtonTitle: 'Download & install agent' as TranslatedString,
      hideButtonTitle: 'Ignore for this host' as TranslatedString,
      closeButtonTitle: 'Close & run service discovery' as TranslatedString,
      agentSlideout,
      isNotRegistered: false,
      noTlsProvided: false,
      isPushMode: false,
      siteId: 'test-site',
      siteServer: 'https://monitoring.example.test',
      agentReceiverPort: 8000,
      agentReceiverPortIsDefault: false
    }
  })
}

interface Layout {
  contentRight: number
  containerWidth: number
  hintHeight?: number
}

const TABLE_LEFT = 50
const CONTAINER_TOP = 100
const TRIGGER_TOP = 140

function stubLayout(layout: Layout) {
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    if (this.id === 'content_area') {
      return new DOMRect(0, 0, layout.contentRight, 800)
    }
    if (this.classList.contains('message_container')) {
      return new DOMRect(TABLE_LEFT, CONTAINER_TOP, layout.containerWidth, 150)
    }
    if (this.tagName === 'TABLE') {
      return new DOMRect(TABLE_LEFT, CONTAINER_TOP, layout.containerWidth, 150)
    }
    if (this.parentElement?.classList.contains('agent_hint')) {
      return new DOMRect(0, TRIGGER_TOP, 0, 16)
    }
    return new DOMRect(0, 0, 0, layout.hintHeight ?? 0)
  })
}

interface DiscoveryPage {
  messageContainer: HTMLElement
  hintTrigger: () => Element | null
}

function renderInDiscoveryPage(layout: Layout): DiscoveryPage {
  stubLayout(layout)
  const page = document.createElement('div')
  page.innerHTML = `
    <div id="content_area">
      <div id="datasources_container">
        <div class="message_container">
          <table><tr><td>[agent] Communication failed</td><td class="agent_hint"></td></tr></table>
        </div>
      </div>
    </div>`
  document.body.appendChild(page)
  onTestFinished(() => page.remove())
  renderDialog(page.querySelector<HTMLElement>('td.agent_hint')!)
  deliverSize(layout.containerWidth, 150)
  return {
    messageContainer: page.querySelector<HTMLElement>('.message_container')!,
    hintTrigger: () => page.querySelector('td.agent_hint [data-agent-hint="open"]')
  }
}

const WIDE: Layout = { contentRight: 1300, containerWidth: 1050 }
const NARROW_BESIDE_LONG_ROWS: Layout = { contentRight: 940, containerWidth: 900 }

useFakeResizeObserver(FakeResizeObserver)

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('hides the hint while the install slide-in is open', async () => {
  renderDialog()
  expect(await screen.findByText(HINT_TITLE)).toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: 'Download & install agent' }))

  expect(await screen.findByRole('dialog', { name: /Install Checkmk agent/ })).toBeInTheDocument()
  await waitFor(() => expect(screen.queryByText(HINT_TITLE)).not.toBeInTheDocument())
})

test('shows the hint again after the slide-in is closed without running discovery', async () => {
  renderDialog()
  await fireEvent.click(await screen.findByRole('button', { name: 'Download & install agent' }))
  const slideIn = await screen.findByRole('dialog', { name: /Install Checkmk agent/ })

  await fireEvent.click(within(slideIn).getByRole('button', { name: 'Close' }))

  expect(await screen.findByText(HINT_TITLE)).toBeInTheDocument()
})

test('shows the hint beside the rows when there is room right of the widest table', async () => {
  const page = renderInDiscoveryPage(WIDE)

  await waitFor(() => expect(page.hintTrigger()).not.toBeNull())
  expect(within(page.messageContainer).queryByText(HINT_TITLE)).not.toBeInTheDocument()
  expect(screen.getByText(HINT_TITLE)).toBeInTheDocument()
})

test('moves the hint below the rows when the widest table leaves too little room', async () => {
  const page = renderInDiscoveryPage(NARROW_BESIDE_LONG_ROWS)

  expect(await within(page.messageContainer).findByText(HINT_TITLE)).toBeInTheDocument()
  expect(page.hintTrigger()).toBeNull()
})

test('moves the hint below the rows when the window gets narrower', async () => {
  const page = renderInDiscoveryPage(WIDE)
  await waitFor(() => expect(page.hintTrigger()).not.toBeNull())

  stubLayout(NARROW_BESIDE_LONG_ROWS)
  deliverSize(NARROW_BESIDE_LONG_ROWS.containerWidth, 150)

  expect(await within(page.messageContainer).findByText(HINT_TITLE)).toBeInTheDocument()
  expect(page.hintTrigger()).toBeNull()
})

test('marks the row of the hint only while the hint is open beside it', async () => {
  const page = renderInDiscoveryPage(WIDE)
  await waitFor(() => expect(page.hintTrigger()).not.toBeNull())

  await fireEvent.click(screen.getByRole('button', { name: 'Download & install agent' }))

  await waitFor(() => expect(page.hintTrigger()).toBeNull())
})

test('ignoring the hint beside the rows removes it and the row mark', async () => {
  const page = renderInDiscoveryPage(WIDE)
  await waitFor(() => expect(page.hintTrigger()).not.toBeNull())

  await fireEvent.click(screen.getByRole('button', { name: 'Ignore for this host' }))

  await waitFor(() => expect(screen.queryByText(HINT_TITLE)).not.toBeInTheDocument())
  expect(page.hintTrigger()).toBeNull()
})

test('ignoring the hint below the rows removes it', async () => {
  const page = renderInDiscoveryPage(NARROW_BESIDE_LONG_ROWS)
  const alert = await within(page.messageContainer).findByText(HINT_TITLE)
  expect(alert).toBeInTheDocument()

  await fireEvent.click(
    within(page.messageContainer).getByRole('button', { name: 'Ignore for this host' })
  )

  await waitFor(() => expect(screen.queryByText(HINT_TITLE)).not.toBeInTheDocument())
})

test('grows the data source box to the bottom of the hint beside the rows', async () => {
  const page = renderInDiscoveryPage({ ...WIDE, hintHeight: 280 })
  await screen.findByText(HINT_TITLE)

  deliverSize(WIDE.containerWidth, 150)

  await waitFor(() =>
    expect(page.messageContainer.style.minHeight).toBe(`${TRIGGER_TOP - CONTAINER_TOP + 280}px`)
  )
})

test('releases the data source box height when the hint is ignored', async () => {
  const page = renderInDiscoveryPage({ ...WIDE, hintHeight: 280 })
  await screen.findByText(HINT_TITLE)
  deliverSize(WIDE.containerWidth, 150)
  await waitFor(() => expect(page.messageContainer.style.minHeight).not.toBe(''))

  await fireEvent.click(screen.getByRole('button', { name: 'Ignore for this host' }))

  await waitFor(() => expect(page.messageContainer.style.minHeight).toBe(''))
})
