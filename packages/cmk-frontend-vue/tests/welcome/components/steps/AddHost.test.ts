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
const CLOUD = { add_host: 'cse-first-host-slideout' }
const RELAYS = { relays: 'wato.py?mode=relays' }

const renderAddHost = (overrides: Partial<WelcomeCards>) =>
  render(
    defineComponent({
      setup: () => () =>
        h(CmkAccordionStepPanel, { modelValue: ['step-1'] }, () =>
          h(AddHost, {
            step: 1,
            stepId: 'add_host',
            cards: { ...createMockCards(), ...overrides },
            accomplished: false
          })
        )
    })
  )

test('Cloud with relays shows the relay alert', () => {
  renderAddHost({ ...CLOUD, ...RELAYS })

  expect(screen.getByText(RELAY_ALERT)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_NOTE)).not.toBeInTheDocument()
})

test('other editions with relays show the relay note', () => {
  renderAddHost(RELAYS)

  expect(screen.getByText(RELAY_NOTE)).toBeInTheDocument()
  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
})

test('without relays neither alert nor note is shown', () => {
  renderAddHost(CLOUD)

  expect(screen.queryByText(RELAY_ALERT)).not.toBeInTheDocument()
  expect(screen.queryByText(RELAY_NOTE)).not.toBeInTheDocument()
})
