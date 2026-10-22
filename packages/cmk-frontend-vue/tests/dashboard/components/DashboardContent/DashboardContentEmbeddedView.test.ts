/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it, onTestFinished } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardContentEmbeddedView from '@/dashboard/components/DashboardContent/DashboardContentEmbeddedView.vue'
import { useProvideDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import type { EmbeddedViewContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

const EMBEDDED_VIEW: EmbeddedViewContent = {
  type: 'embedded_view',
  embedded_id: 'view-1',
  datasource: 'hosts',
  restricted_to_single: []
}

function iframeVariables(drillDownSource: string | null): URLSearchParams {
  const dashboard = defineComponent({
    setup() {
      if (drillDownSource !== null) {
        useProvideDrillDownSource(ref(drillDownSource))
      }
      return () => h(DashboardContentEmbeddedView, makeContentProps(EMBEDDED_VIEW))
    }
  })
  const { container } = render(dashboard)
  const source = container.querySelector('iframe')!.getAttribute('src')!
  return new URL(source, window.location.href).searchParams
}

describe('DashboardContentEmbeddedView', () => {
  it('hands its column drill-downs the dashboard to lead back to', () => {
    window.history.replaceState({}, '', '/dashboard.py?name=main&_drilled_from=Other')
    onTestFinished(() => window.history.replaceState({}, '', '/'))

    const variables = iframeVariables('Overview')

    expect(variables.get('drill_down_source_title')).toBe('Overview')
    expect(variables.get('drill_down_source_url')).toBe(
      `${window.location.origin}/dashboard.py?name=main&_drilled_from=Other`
    )
  })

  it('hands no way back where nothing names the dashboard', () => {
    expect(iframeVariables(null).has('drill_down_source_title')).toBe(false)
  })
})
