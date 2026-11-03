/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'

import WizardSelector from '@/dashboard/components/WizardSelector/WizardSelector.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

vi.mock('cmk-ui-library/components/CmkSlideIn', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      setup:
        (_props, { slots }) =>
        () =>
          h('div', slots.default?.())
    })
  }
})

vi.mock('@/dashboard/components/Wizard/wizards/custom-graphs/CustomGraphsWizard.vue', async () => {
  const { defineComponent, h } = await import('vue')
  return {
    default: defineComponent({
      emits: ['cloneGraph'],
      setup:
        (_props, { emit }) =>
        () =>
          h('button', { onClick: () => emit('cloneGraph', 'my_graph') }, 'Clone & edit graph')
    })
  }
})

vi.mock(
  '@/dashboard/components/Wizard/wizards/custom-graphs/CloneCustomGraphWizard.vue',
  async () => {
    const { defineComponent, h } = await import('vue')
    return {
      default: defineComponent({
        props: { linkedGraph: { type: String, default: null } },
        emits: ['addWidget'],
        setup:
          (props, { emit }) =>
          () =>
            h(
              'button',
              { onClick: () => emit('addWidget', { type: 'embedded_custom_graph' }, {}, {}) },
              `Save copy of ${props.linkedGraph}`
            )
      })
    }
  }
)

const LINKED_WIDGET = {
  content: { type: 'custom_graph', custom_graph: 'my_graph' }
} as unknown as WidgetSpec

function renderSelector() {
  const onEditWidget = vi.fn()
  render(WizardSelector, {
    props: {
      tick: 0,
      range: makeContentProps(null).range,
      isOpen: true,
      selectedWizard: 'link_custom_graph',
      dashboardKey: { name: 'main', owner: '' },
      contextFilters: {},
      editWidgetSpec: LINKED_WIDGET,
      editWidgetId: 'widget-1',
      dashboardFeatures: DashboardFeatures.UNRESTRICTED,
      'onEdit-widget': onEditWidget
    }
  })
  return { onEditWidget }
}

describe('WizardSelector', () => {
  test('switches a linked widget to the clone wizard with its graph', async () => {
    renderSelector()

    await fireEvent.click(screen.getByRole('button', { name: 'Clone & edit graph' }))

    expect(screen.getByRole('button', { name: 'Save copy of my_graph' })).toBeInTheDocument()
  })

  test('replaces a switched linked widget in place', async () => {
    const { onEditWidget } = renderSelector()
    await fireEvent.click(screen.getByRole('button', { name: 'Clone & edit graph' }))

    await fireEvent.click(screen.getByRole('button', { name: 'Save copy of my_graph' }))

    expect(onEditWidget).toHaveBeenCalledWith('widget-1', { type: 'embedded_custom_graph' }, {}, {})
  })
})
