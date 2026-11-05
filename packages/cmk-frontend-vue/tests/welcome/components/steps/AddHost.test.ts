/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkAccordionStepPanel from 'cmk-ui-library/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import { defineComponent, h } from 'vue'

import AddHost from '@/welcome/components/steps/AddHost.vue'

import { createMockCards } from '../../mockCards'

const RELAY_ALERT = 'Network devices and virtualization need a Checkmk Relay'
const RELAY_NOTE = /Systems behind a firewall\?/
const RELAY_FIRST = 'Set up a Checkmk Relay first'
const RELAY_ONLY = ['Switches, routers, firewalls & other SNMP devices', 'Proxmox VE']
const CLOUD = { add_host: 'cse-first-host-slideout' }
const RELAYS = { relays: 'wato.py?mode=relays' }
// The mock cards keep their network devices link: the flag alone decides.
const CLOUD_WITHOUT_RELAY = { ...CLOUD, ...RELAYS, relay_configured: false }
const CLOUD_WITH_RELAY = { ...CLOUD, ...RELAYS, relay_configured: true }

const renderAddHost = (overrides: Partial<WelcomeCards>, base = createMockCards()) =>
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

const cardOf = (title: string) => screen.getByText(title).closest('.cmk-link-card')

test('Cloud without a configured relay shows the relay alert', () => {
  renderAddHost(CLOUD_WITHOUT_RELAY)

  expect(screen.getByText(RELAY_ALERT)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_NOTE)).not.toBeInTheDocument()
})

test.each(RELAY_ONLY)('Cloud without a configured relay greys out %s with a note', (title) => {
  renderAddHost(CLOUD_WITHOUT_RELAY)

  expect(cardOf(title)).toHaveClass('disabled')
  expect(cardOf(title)).not.toHaveAttribute('href')
  expect(cardOf(title)).toHaveTextContent(RELAY_FIRST)
})

test.each(RELAY_ONLY)('Cloud with a configured relay links %s', (title) => {
  renderAddHost(CLOUD_WITH_RELAY)

  expect(cardOf(title)).not.toHaveClass('disabled')
  expect(cardOf(title)).toHaveAttribute('href')
  expect(screen.queryByText(RELAY_FIRST)).not.toBeInTheDocument()
  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
})

test('other editions with relays show the relay note', () => {
  renderAddHost(RELAYS)

  expect(screen.getByText(RELAY_NOTE)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
})

test('Cloud without the relay feature shows no relay hints and greys out nothing', () => {
  // Without the relay feature, Cloud registers no network devices card.
  const { network_devices: _, ...cards } = createMockCards()
  renderAddHost(CLOUD, cards)

  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
  expect(screen.queryByText(RELAY_NOTE)).not.toBeInTheDocument()
  expect(screen.queryByText(RELAY_FIRST)).not.toBeInTheDocument()
  expect(cardOf('Proxmox VE')).toHaveAttribute('href')
  expect(screen.queryByText(RELAY_ONLY[0]!)).not.toBeInTheDocument()
})
