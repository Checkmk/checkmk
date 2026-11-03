/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardPreviewContent from '@/dashboard/components/DashboardPreviewContent.vue'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { AverageScatterplotContent, StaticTextContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

// The figure owns its own data fetch; the preview only decides how the widget around it scrolls.
vi.mock('@/graphing/components/GraphFigure/GraphFigure.vue', () => ({
  default: { template: '<div data-testid="graph-figure" />' }
}))

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

  it('lets the legend of a scatterplot scroll', async () => {
    vi.spyOn(client, 'POST').mockResolvedValue({
      data: {
        graphs: [{ internal: '{"graphs": []}', title: 'Scatterplot' }],
        no_data_message: null
      },
      error: undefined,
      response: new Response('{}', { status: 200 })
    } as never)
    const props = makeContentProps<AverageScatterplotContent>({
      type: 'average_scatterplot',
      metric: 'util',
      time_range: { type: 'predefined', value: 'last_25_hours' },
      metric_color: 'default',
      average_color: 'default',
      median_color: 'default',
      show_legend: true
    })

    renderPreview(props)

    await screen.findByTestId('graph-figure')
    expect(document.querySelector('.db-content-container__preview-scroll-container')).not.toBeNull()
  })
})
