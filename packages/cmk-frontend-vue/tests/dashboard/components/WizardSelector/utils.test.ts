/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  DASHBOARD_WIDGET_WORKFLOW_KEYS,
  type DashboardWidgetWorkflowKey
} from '@/dashboard/components/WidgetWorkflow/WidgetWorkflowTypes'
import {
  widgetTypeToSelectorMatcher,
  wizardSlideInSize
} from '@/dashboard/components/WizardSelector/utils'

describe('widgetTypeToSelectorMatcher', () => {
  it('edits a custom graph widget in the link-existing custom graph wizard', () => {
    const contentType = 'custom_graph'

    const wizardKey = widgetTypeToSelectorMatcher(contentType)

    expect(wizardKey).toBe('link_custom_graph')
  })

  it.each(['linked_view', 'embedded_view'] as const)(
    'edits a %s widget in the classic view wizard',
    (contentType) => {
      expect(widgetTypeToSelectorMatcher(contentType)).toBe('classic_view')
    }
  )

  it('edits a monitoring table widget in the view wizard', () => {
    const wizardKey = widgetTypeToSelectorMatcher('monitoring_table')

    expect(wizardKey).toBe('view')
  })

  it('has no wizard to edit an embedded custom graph widget in yet', () => {
    const wizardKey = widgetTypeToSelectorMatcher('embedded_custom_graph')

    expect(wizardKey).toBeNull()
  })
})

describe('wizardSlideInSize', () => {
  const small: DashboardWidgetWorkflowKey[] = ['other', 'ntop']
  const large: DashboardWidgetWorkflowKey[] = ['view', 'classic_view']
  const medium = DASHBOARD_WIDGET_WORKFLOW_KEYS.filter(
    (key) => !small.includes(key) && !large.includes(key)
  )

  it.each(small)('opens the %s wizard in a small slide-in', (wizard) => {
    expect(wizardSlideInSize(wizard)).toBe('small')
  })

  it.each(medium)('opens the %s wizard in a medium slide-in', (wizard) => {
    expect(wizardSlideInSize(wizard)).toBe('medium')
  })

  it.each(large)('opens the %s wizard in a large slide-in', (wizard) => {
    expect(wizardSlideInSize(wizard)).toBe('large')
  })
})
