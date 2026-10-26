/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { describe, expect, it } from 'vitest'

import {
  type WorkflowCatalog,
  type WorkflowGroup,
  type WorkflowItem,
  findParentWorkflowKey,
  getDashboardWidgetWorkflows
} from '@/dashboard/components/WidgetWorkflow/WidgetWorkflowTypes'

function workflowItem(title: string): WorkflowItem {
  return { title: title as TranslatedString, subtitle: '' as TranslatedString, icon: 'graph' }
}

const catalogWithTwoGroups: WorkflowCatalog = {
  single_workflow: workflowItem('Single workflow'),
  first_group: {
    ...workflowItem('First group'),
    subWorkflows: { first_group_entry: workflowItem('First group entry') }
  },
  second_group: {
    ...workflowItem('Second group'),
    subWorkflows: { second_group_entry: workflowItem('Second group entry') }
  }
}

describe('findParentWorkflowKey', () => {
  it('finds the group that lists a sub-workflow', () => {
    const subWorkflowKey = 'second_group_entry'

    const parentKey = findParentWorkflowKey(catalogWithTwoGroups, subWorkflowKey)

    expect(parentKey).toBe('second_group')
  })

  it('finds no group for a top-level workflow', () => {
    const topLevelKey = 'single_workflow'

    const parentKey = findParentWorkflowKey(catalogWithTwoGroups, topLevelKey)

    expect(parentKey).toBeNull()
  })
})

describe('getDashboardWidgetWorkflows', () => {
  it('offers the link-existing custom graph wizard inside the custom graphs group', () => {
    const dashboardCatalog = getDashboardWidgetWorkflows()

    const parentKey = findParentWorkflowKey(dashboardCatalog, 'link_custom_graph')

    expect(parentKey).toBe('custom_graphs')
  })

  it('offers creating a custom graph to every user', () => {
    const dashboardCatalog = getDashboardWidgetWorkflows({ mayEditCustomGraph: false })

    const newEntry = (dashboardCatalog['custom_graphs'] as WorkflowGroup).subWorkflows[
      'new_custom_graph'
    ]

    expect(newEntry?.unavailableReason).toBeUndefined()
  })

  it('disables cloning for users who may not edit custom graphs', () => {
    const dashboardCatalog = getDashboardWidgetWorkflows({ mayEditCustomGraph: false })

    const cloneEntry = (dashboardCatalog['custom_graphs'] as WorkflowGroup).subWorkflows[
      'clone_custom_graph'
    ]

    expect(cloneEntry?.unavailableReason).toContain('Customize and use custom graphs')
  })

  it.each(['view', 'classic_view'])('offers the %s wizard inside the views group', (key) => {
    const dashboardCatalog = getDashboardWidgetWorkflows()

    const parentKey = findParentWorkflowKey(dashboardCatalog, key)

    expect(parentKey).toBe('views')
  })
})
