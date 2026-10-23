/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import AddWidgetDialog from '@/dashboard/components/WidgetWorkflow/StarterDialog/AddWidgetDialog.vue'
import {
  type WorkflowCatalog,
  getDashboardWidgetWorkflows
} from '@/dashboard/components/WidgetWorkflow/WidgetWorkflowTypes'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

function slideInWithoutRekaDialog() {
  return defineComponent({
    name: 'CmkSlideIn',
    props: {
      open: { type: Boolean, required: true },
      ariaLabel: { type: String, default: undefined }
    },
    setup(props, { slots }) {
      return () =>
        props.open
          ? h('div', { role: 'dialog', 'aria-label': props.ariaLabel }, slots.default?.())
          : null
    }
  })
}

vi.mock('cmk-ui-library/components/CmkSlideIn', () => ({ default: slideInWithoutRekaDialog() }))

const catalogWithOneGroup: WorkflowCatalog = {
  single_workflow: {
    title: 'Single workflow' as TranslatedString,
    subtitle: 'Opens its wizard directly' as TranslatedString,
    icon: 'graph'
  },
  grouped_workflows: {
    title: 'Grouped workflows' as TranslatedString,
    subtitle: 'Offers a choice of workflows' as TranslatedString,
    icon: 'graph',
    subWorkflows: {
      unfinished_workflow: {
        title: 'Unfinished workflow' as TranslatedString,
        subtitle: 'Cannot be chosen yet' as TranslatedString,
        icon: 'graph',
        unavailableReason: 'Not ready yet' as TranslatedString
      },
      ready_workflow: {
        title: 'Ready workflow' as TranslatedString,
        subtitle: 'Can be chosen' as TranslatedString,
        icon: 'graph'
      }
    }
  }
}

interface RenderOptions {
  startingGroupKey?: string | null
  catalog?: WorkflowCatalog
  dashboardFeatures?: DashboardFeatures
}

function renderAddWidgetDialog({
  startingGroupKey = null,
  catalog = catalogWithOneGroup,
  dashboardFeatures = DashboardFeatures.UNRESTRICTED
}: RenderOptions = {}) {
  const activeGroupKey = ref<string | null>(startingGroupKey)
  const wrapper = defineComponent({
    setup() {
      return () =>
        h(AddWidgetDialog, {
          open: true,
          workflowItems: catalog,
          dashboardFeatures,
          activeGroupKey: activeGroupKey.value,
          'onUpdate:activeGroupKey': (groupKey: string | null) => (activeGroupKey.value = groupKey)
        })
    }
  })
  const user = userEvent.setup()
  render(wrapper)
  return { user }
}

describe('AddWidgetDialog', () => {
  it('shows the entries of a group once the group is chosen', async () => {
    const { user } = renderAddWidgetDialog()

    await user.click(screen.getByRole('button', { name: /Grouped workflows/ }))

    expect(screen.getByRole('button', { name: /Ready workflow/ })).toBeInTheDocument()
  })

  it('opens directly on the entries of the group it starts on', () => {
    renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    expect(screen.getByRole('button', { name: /Ready workflow/ })).toBeInTheDocument()
  })

  it('names the shown group in the heading', () => {
    renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    expect(screen.getByRole('heading', { level: 1, name: 'Grouped workflows' })).toBeInTheDocument()
  })

  it('shows the top-level entries again after going back', async () => {
    const { user } = renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.getByRole('button', { name: /Single workflow/ })).toBeInTheDocument()
  })

  it('focuses the first available entry after entering a group', async () => {
    const { user } = renderAddWidgetDialog()

    await user.click(screen.getByRole('button', { name: /Grouped workflows/ }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Ready workflow/ })).toHaveFocus()
    )
  })

  it('focuses the group entry after going back', async () => {
    const { user } = renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    await user.click(screen.getByRole('button', { name: 'Back' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Grouped workflows/ })).toHaveFocus()
    )
  })

  it('disables an unavailable entry', () => {
    renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    expect(screen.getByRole('button', { name: /Unfinished workflow/ })).toBeDisabled()
  })

  it('shows why an entry is unavailable', () => {
    renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    expect(screen.getByTitle('Not ready yet')).toBeInTheDocument()
  })

  it('keeps its accessible name while a group is shown', () => {
    renderAddWidgetDialog({ startingGroupKey: 'grouped_workflows' })

    expect(screen.getByRole('dialog', { name: 'Add widget' })).toBeInTheDocument()
  })

  it('cannot open the custom graphs group in the restricted edition', () => {
    renderAddWidgetDialog({
      catalog: getDashboardWidgetWorkflows(),
      dashboardFeatures: DashboardFeatures.RESTRICTED
    })

    expect(screen.getByRole('button', { name: /^Custom graphs/ })).toBeDisabled()
  })
})
