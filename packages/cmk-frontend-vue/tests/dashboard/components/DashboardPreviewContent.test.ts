/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { AverageScatterplotContent, StaticTextContent } from '@/dashboard/types/widget'

import { discoveredGraph } from '@tests/dashboard/apiHandlers'
import { makeContentProps } from '@tests/dashboard/contentProps'

// The figure owns its own data fetch; the preview only decides how the widget around it scrolls.
vi.mock('@/graphing/components/GraphFigure/GraphFigure.vue', () => ({
  default: { template: '<div data-testid="graph-figure" />' }
}))

useMswServer(
  restApiHttp.post(
    '/domain-types/graph/actions/discover_average_scatterplot_graphs/invoke',
    ({ response }) =>
      response(200).json({
        graphs: [discoveredGraph('scatterplot', 'Scatterplot', '{"graphs": []}')],
        no_data_message: null
      })
  )
)

function renderPreview(props: object) {
  const wrapper = defineComponent({
    setup() {
      useProvideMissingRuntimeFiltersAction(ref(true), () => {})
      return () => h(DashboardPreviewContent, props as never)
    }
  })
  return render(wrapper)
}

describe('DashboardPreviewContent', () => {
  it('renders a linked title as plain text', () => {
    const props = makeContentProps<StaticTextContent>(
      { type: 'static_text', text: 'Hello' },
      {
        general_settings: {
          title: {
            text: 'Test',
            url: 'view.py?view_name=allhosts',
            render_mode: 'with_background'
          },
          render_background: true
        }
      }
    )

    renderPreview(props)

    expect(screen.getByRole('heading', { name: 'Test' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Test' })).toBeNull()
  })

  it.each([
    { legend: 'extended', scrolls: true },
    { legend: 'compact', scrolls: false }
  ] as const)(
    'scrolls a scatterplot preview with a $legend legend: $scrolls',
    async ({ legend, scrolls }) => {
      const props = makeContentProps<AverageScatterplotContent>({
        type: 'average_scatterplot',
        metric: 'util',
        time_range: { type: 'predefined', value: 'last_25_hours' },
        metric_color: 'default',
        average_color: 'default',
        median_color: 'default',
        legend,
        contextual_link: { type: 'none' }
      })

      renderPreview(props)

      await screen.findByTestId('graph-figure')
      const scrollContainer = document.querySelector(
        '.db-content-container__preview-scroll-container'
      )
      expect(scrollContainer !== null).toBe(scrolls)
    }
  )
})
