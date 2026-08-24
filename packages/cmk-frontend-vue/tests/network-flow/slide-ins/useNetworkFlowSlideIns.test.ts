/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'
import { defineComponent, h, inject, nextTick } from 'vue'

import {
  donutOtherBreakdownSlideInKey,
  hostSlideInKey
} from '@/network-flow/slide-ins/injectionKeys'
import {
  type NetworkFlowSlideIns,
  useNetworkFlowSlideIns
} from '@/network-flow/slide-ins/useNetworkFlowSlideIns'

// The openers are provided, so the trigger has to sit below the owner - which is
// also how a widget reaches them.
const triggerComponent = defineComponent({
  setup() {
    const openHost = inject(hostSlideInKey)!
    const openBreakdown = inject(donutOtherBreakdownSlideInKey)!
    return () => [
      h('button', { onClick: () => openHost('10.0.0.1') }, 'open host'),
      h(
        'button',
        {
          onClick: () =>
            openBreakdown({
              content: {
                type: 'network_flow_donut',
                dimension: 'applications',
                limit_to: 6,
                legend_mode: 'table',
                show_delta: false
              },
              context: {},
              window: { start: 1_000, end: 1_900 }
            })
        },
        'open breakdown'
      )
    ]
  }
})

test('puts the keyboard back where the panel was opened from', async () => {
  let slideIns: NetworkFlowSlideIns | null = null
  const owner = defineComponent({
    setup() {
      slideIns = useNetworkFlowSlideIns()
      return () => h(triggerComponent)
    }
  })
  const { getByRole } = render(owner)
  const trigger = getByRole('button', { name: 'open host' })

  trigger.focus()
  await fireEvent.click(trigger)
  expect(slideIns!.hostOpen.value).toBe(true)

  // What the panel does on open: focus moves off the trigger and into the dialog.
  trigger.blur()
  expect(document.activeElement).not.toBe(trigger)

  slideIns!.closeHost()
  await nextTick()
  await nextTick()

  expect(document.activeElement).toBe(trigger)
})

test('restores each panel to its own trigger, whatever order they close in', async () => {
  let slideIns: NetworkFlowSlideIns | null = null
  const owner = defineComponent({
    setup() {
      slideIns = useNetworkFlowSlideIns()
      return () => h(triggerComponent)
    }
  })
  const { getByRole } = render(owner)
  const hostTrigger = getByRole('button', { name: 'open host' })
  const breakdownTrigger = getByRole('button', { name: 'open breakdown' })

  // Nothing traps focus, so a second panel can be opened from behind the first.
  hostTrigger.focus()
  await fireEvent.click(hostTrigger)
  breakdownTrigger.focus()
  await fireEvent.click(breakdownTrigger)
  breakdownTrigger.blur()

  slideIns!.closeDonutOther()
  await nextTick()
  await nextTick()
  expect(document.activeElement).toBe(breakdownTrigger)
  ;(document.activeElement as HTMLElement).blur()
  slideIns!.closeHost()
  await nextTick()
  await nextTick()

  expect(document.activeElement).toBe(hostTrigger)
})
