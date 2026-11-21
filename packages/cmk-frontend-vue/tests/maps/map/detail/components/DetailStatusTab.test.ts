/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DetailStatusTab from '@/maps/map/detail/components/DetailStatusTab.vue'

import { aDetails, aState, anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

function renderTab(state: string, selectableHosts: string[] = [], hostsUp = new Set<string>()) {
  const selected: string[] = []
  render(DetailStatusTab, {
    props: {
      object: anObject({ id: 'h1', type: 'host', host_name: 'app01' }),
      state: aState({ object_id: 'h1', type: 'host', state }),
      details: aDetails({ type: 'host', host_name: 'app01', parents: ['switch01'] }),
      displayName: 'app01',
      checkmkUrl: null,
      hostChips: [],
      serviceChips: [],
      nowMs: 0,
      selectableHosts,
      hostsUp,
      'onSelect-host': (hostName: string) => selected.push(hostName)
    },
    global: mapsGlobal()
  })
  return selected
}

describe('DetailStatusTab', () => {
  it('names the parents an unreachable host is reached through', async () => {
    const selected = renderTab('UNREACHABLE', ['switch01'])
    expect(screen.getByText('Unreachable through')).toBeInTheDocument()
    await userEvent.click(screen.getByText('switch01'))
    expect(selected).toEqual(['switch01'])
  })

  it('leaves out a parent that is up', () => {
    renderTab('UNREACHABLE', ['switch01'], new Set(['switch01']))
    expect(screen.queryByText('Unreachable through')).toBeNull()
  })

  it('says nothing about parents of a host that is up', () => {
    renderTab('UP')
    expect(screen.queryByText('Unreachable through')).toBeNull()
  })
})
