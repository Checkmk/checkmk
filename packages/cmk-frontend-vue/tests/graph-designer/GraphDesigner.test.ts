/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'

import GraphDesignerApp from '@/graph-designer/GraphDesignerApp.vue'
import { type AjaxGraph } from '@/graph-designer/private/graph.ts'

const server = setupServer(
  http.post('ajax_fetch_ajax_graph.py', () => {
    return HttpResponse.json({ result_code: 0, result: {} })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterAll(() => server.close())

async function fakeGraphRenderer(_ajaxGraph: AjaxGraph, _container: HTMLDivElement) {
  return
}

test('Render GraphDesignerApp', () => {
  render(GraphDesignerApp, {
    props: {
      graph_id: 'graph id',
      graph_lines: [],
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      },
      metric_backend_available: false,
      create_services_available: false,
      graph_renderer: fakeGraphRenderer
    }
  })
})
