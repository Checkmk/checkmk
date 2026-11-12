/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { defineComponent, h } from 'vue'

import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'

import AddHost from '@/welcome/components/steps/AddHost.vue'

import { createMockCards } from '../../mockCards'

const RELAY_ALERT = 'Network devices need a Checkmk Relay'
const RELAY_NOTE = /Systems behind a firewall\?/
const RELAY_FIRST = 'Set up a Checkmk Relay first'
const RELAY_ONLY = ['Switches, routers, firewalls & other SNMP devices']
const CLOUD = { add_host: 'cse-first-host-slideout' }
const RELAYS = { relays: 'wato.py?mode=relays' }
// The mock cards keep their network devices link: the flag alone decides.
const CLOUD_WITHOUT_RELAY = { ...CLOUD, ...RELAYS, relay_configured: false }
const CLOUD_WITH_RELAY = { ...CLOUD, ...RELAYS, relay_configured: true }

// The accordion mounts its content a tick after rendering, so wait for it.
const renderAddHost = async (overrides: Partial<WelcomeCards>, base = createMockCards()) => {
  render(
    defineComponent({
      setup: () => () =>
        h(CmkAccordionStepPanel, { modelValue: ['step-1'] }, () =>
          h(AddHost, {
            step: 1,
            stepId: 'add_host',
            cards: { ...base, ...overrides },
            accomplished: false
          })
        )
    })
  )
  await screen.findByText('Cloud platforms')
}

const cardOf = (title: string) => screen.getByText(title).closest('.cmk-link-card')

test('Cloud without a configured relay shows the relay alert', async () => {
  await renderAddHost(CLOUD_WITHOUT_RELAY)

  expect(screen.getByText(RELAY_ALERT)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_NOTE)).not.toBeInTheDocument()
})

test.each(RELAY_ONLY)(
  'Cloud without a configured relay greys out %s with a note',
  async (title) => {
    await renderAddHost(CLOUD_WITHOUT_RELAY)

    expect(cardOf(title)).toHaveClass('disabled')
    // A link card without a URL links to '#' and blocks the click.
    expect(cardOf(title)).toHaveAttribute('href', '#')
    expect(cardOf(title)).toHaveTextContent(RELAY_FIRST)
  }
)

test.each(RELAY_ONLY)('Cloud with a configured relay links %s', async (title) => {
  await renderAddHost(CLOUD_WITH_RELAY)

  expect(cardOf(title)).not.toHaveClass('disabled')
  expect(cardOf(title)).toHaveAttribute('href')
  expect(screen.queryByText(RELAY_FIRST)).not.toBeInTheDocument()
  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
})

test('other editions with relays show the relay note', async () => {
  await renderAddHost(RELAYS)

  expect(screen.getByText(RELAY_NOTE)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
})
