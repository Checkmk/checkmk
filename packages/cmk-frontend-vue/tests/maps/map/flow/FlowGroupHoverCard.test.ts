/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import FlowGroupHoverCard, {
  type GroupCardContent
} from '@/maps/map/flow/components/FlowGroupHoverCard.vue'

import { mapsGlobal } from '../../support/services'

const NONE = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 }

function content(pressing: number, pressingCount = pressing): GroupCardContent {
  return {
    name: '60 hosts',
    subtitle: 'Hosts below core',
    state: 'CRITICAL',
    summary: { hosts: NONE, services: { ...NONE, critical: pressing } },
    viewTarget: { hosts: [] },
    pressing: Array.from({ length: pressing }, (_, i) => ({
      name: `host-${i}`,
      needs: 'critical' as const
    })),
    pressingCount
  }
}

function renderCard(card: GroupCardContent) {
  return render(FlowGroupHoverCard, {
    props: {
      content: card,
      x: 0,
      y: 0,
      around: { left: 0, top: 0, right: 0, bottom: 0 },
      checkmkUrl: null
    },
    global: mapsGlobal()
  })
}

// The card stays hidden until it is placed, which needs a layout jsdom lacks.
const hidden = { hidden: true }

describe('FlowGroupHoverCard', () => {
  it('stays open when more hosts are shown, focus on the first one added', async () => {
    const { emitted } = renderCard(content(5))

    await userEvent.click(screen.getByText('Show 2 more'))

    expect(screen.getAllByRole('button', { name: /^host-/, ...hidden })).toHaveLength(5)
    expect(document.activeElement).toBe(screen.getByRole('button', { name: /^host-3,/, ...hidden }))
    expect(emitted('card-leave')).toBeUndefined()
  })

  it('says how many hosts it does not list', async () => {
    renderCard(content(5, 60))

    await userEvent.click(screen.getByText('Show 2 more'))

    expect(screen.getByText('and 55 more')).toBeInTheDocument()
  })
})
